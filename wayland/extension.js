import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GdkPixbuf from 'gi://GdkPixbuf';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {BackgroundManager} from 'resource:///org/gnome/shell/ui/background.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {WorkspaceThumbnail} from 'resource:///org/gnome/shell/ui/workspaceThumbnail.js';

function loadImage(file) {
    const pixbuf = GdkPixbuf.Pixbuf.new_from_file(file.get_path());
    const image = new Clutter.Image();
    const format = pixbuf.get_has_alpha() ? Cogl.PixelFormat.RGBA_8888 : Cogl.PixelFormat.RGB_888;
    image.set_bytes(pixbuf.read_pixel_bytes(), format,
        pixbuf.get_width(), pixbuf.get_height(), pixbuf.get_rowstride());
    return image;
}

export default class EyesDesktop extends Extension {
    enable() {
        if (!Meta.is_wayland_compositor())
            return;
        this.assets = this.dir.get_child('frames');
        const [, data] = this.assets.get_child('frames.json').load_contents(null);
        this.info = JSON.parse(new TextDecoder().decode(data));
        this.backdrop = loadImage(this.assets.get_child('backdrop.png'));
        this.layers = new Map();
        this.overviewLayers = [];
        this.thumbnails = new WeakMap();
        this.cached = new Map();
        const [, , width, height] = this.info.patch;
        this.cacheAll = width * height * 4 * this.info.count <= 32 * 1024 * 1024;
        this.activeFrame = -1;
        this.started = GLib.get_monotonic_time();
        this.update();

        const extension = this;
        const prototype = BackgroundManager.prototype;
        const originalCreate = prototype._createBackgroundActor;
        this.originalCreate = originalCreate;
        const createBackground = function (...args) {
            const actor = originalCreate.apply(this, args);
            if (extension.createBackground === createBackground)
                extension.attach(actor);
            return actor;
        };
        this.createBackground = createBackground;
        prototype._createBackgroundActor = createBackground;

        const thumbnailPrototype = WorkspaceThumbnail.prototype;
        const originalPorthole = thumbnailPrototype.setPorthole;
        this.originalPorthole = originalPorthole;
        const setPorthole = function (...args) {
            originalPorthole.apply(this, args);
            if (extension.setPorthole === setPorthole)
                extension.attachThumbnail(this);
        };
        this.setPorthole = setPorthole;
        thumbnailPrototype.setPorthole = setPorthole;

        this.attachExisting(Main.layoutManager._backgroundGroup);
        this.attachExisting(Main.layoutManager.overviewGroup);
        this.refreshOverview();
        this.monitorsSignal = Main.layoutManager.connect('monitors-changed', () => this.refreshOverview());
        this.shutdownSignal = global.connect('shutdown', () => this.disable());
        this.timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, Math.max(10, Math.floor(500 / this.info.fps)), () => {
            this.update();
            return GLib.SOURCE_CONTINUE;
        });
    }

    attachExisting(actor) {
        if (actor instanceof WorkspaceThumbnail)
            this.attachThumbnail(actor);
        if (actor instanceof Meta.BackgroundActor) {
            this.attach(actor);
            return;
        }

        for (const child of actor.get_children())
            this.attachExisting(child);
    }

    attach(background) {
        const layer = this.createLayer();
        layer.add_constraint(new Clutter.BindConstraint({
            source: background,
            coordinate: Clutter.BindCoordinate.SIZE,
        }));
        background.add_child(layer);
    }

    attachThumbnail(thumbnail) {
        const monitor = Main.layoutManager.monitors[thumbnail.monitorIndex];
        if (!monitor)
            return;
        let layer = this.thumbnails.get(thumbnail);
        if (!layer) {
            layer = this.createLayer();
            thumbnail._contents.insert_child_at_index(layer, 0);
            this.thumbnails.set(thumbnail, layer);
        }
        layer.set_position(monitor.x, monitor.y);
        layer.set_size(monitor.width, monitor.height);
    }

    refreshOverview() {
        for (const layer of this.overviewLayers)
            layer.destroy();
        this.overviewLayers = Main.layoutManager.monitors.map(monitor => {
            const layer = this.createLayer();
            layer.opacity = 115;
            layer.set_position(monitor.x, monitor.y);
            layer.set_size(monitor.width, monitor.height);
            Main.layoutManager.overviewGroup.insert_child_at_index(layer, 0);
            return layer;
        });
    }

    createLayer() {
        const layer = new Clutter.Actor({
            content: this.backdrop,
            content_gravity: Clutter.ContentGravity.RESIZE_FILL,
            reactive: false,
        });
        const motion = new Clutter.Actor({
            content: this.frame,
            content_gravity: Clutter.ContentGravity.RESIZE_FILL,
            reactive: false,
        });
        const {width, height, patch: [x, y, w, h]} = this.info;
        layer.add_child(motion);
        layer.connect('notify::allocation', () => {
            const sx = layer.width / width;
            const sy = layer.height / height;
            motion.set_position(x * sx, y * sy);
            motion.set_size(w * sx, h * sy);
        });
        this.layers.set(layer, motion);
        layer.connect('destroy', () => this.layers.delete(layer));
        return layer;
    }

    update() {
        const elapsed = (GLib.get_monotonic_time() - this.started) / 1_000_000;
        const index = Math.floor(elapsed * this.info.fps) % this.info.count;
        if (index === this.activeFrame)
            return;

        let frame = this.cached.get(index);
        if (!frame) {
            frame = loadImage(this.assets.get_child(`frame-${index}.png`));
            if (this.cacheAll)
                this.cached.set(index, frame);
        }
        this.activeFrame = index;
        this.frame = frame;
        for (const motion of this.layers.values())
            motion.content = frame;
    }

    disable() {
        if (this.shutdownSignal) {
            global.disconnect(this.shutdownSignal);
            this.shutdownSignal = 0;
        }
        if (this.timer) {
            GLib.Source.remove(this.timer);
            this.timer = 0;
        }
        if (this.monitorsSignal) {
            Main.layoutManager.disconnect(this.monitorsSignal);
            this.monitorsSignal = 0;
        }
        if (BackgroundManager.prototype._createBackgroundActor === this.createBackground)
            BackgroundManager.prototype._createBackgroundActor = this.originalCreate;
        this.createBackground = this.originalCreate = null;
        if (WorkspaceThumbnail.prototype.setPorthole === this.setPorthole)
            WorkspaceThumbnail.prototype.setPorthole = this.originalPorthole;
        this.setPorthole = this.originalPorthole = null;
        for (const layer of this.layers?.keys() ?? [])
            layer.destroy();
        this.layers = this.cached = this.backdrop = this.frame = this.info = this.assets = null;
        this.overviewLayers = this.thumbnails = null;
    }
}
