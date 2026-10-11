package dev.eldencraft.bridge;

import org.joml.Matrix4fc;
import org.joml.Vector4f;

/** Pure, camera-relative placement of native health gauges in the captured HUD layer. */
public final class EnemyHealthDisplay {
  public record Position(int x, int y) {}

  private EnemyHealthDisplay() {}

  public static boolean sameContext(
      ProxyProtocol.Frame frame, long pid, long map, long ageNanos) {
    return frame != null
        && frame.ready()
        && frame.pid() == pid
        && frame.map() == map
        && ageNanos >= 0
        && ageNanos < 250_000_000L;
  }

  public static boolean visible(ProxyProtocol.Target target, double maxDistance) {
    if (!target.hittable() || !Float.isFinite(target.hp()) || !Float.isFinite(target.maxHp())
        || target.maxHp() <= 0 || target.hp() > target.maxHp()) return false;
    // Distance to the body, rather than its centre: a huge boss can be nearby.
    double x = distance(target.min().x(), target.max().x());
    double y = distance(target.min().y(), target.max().y());
    double z = distance(target.min().z(), target.max().z());
    return x * x + y * y + z * z <= maxDistance * maxDistance;
  }

  private static double distance(double min, double max) {
    return min > 0 ? min : max < 0 ? -max : 0;
  }

  public static ProxyProtocol.Vec head(ProxyProtocol.Target target, double offset) {
    return new ProxyProtocol.Vec(
        (target.min().x() + target.max().x()) / 2,
        target.max().y() + offset,
        (target.min().z() + target.max().z()) / 2);
  }

  /** Anchor above the authored target bounds; never pin off-screen enemies to the screen edge. */
  public static Position project(
      ProxyProtocol.Vec head,
      ProxyProtocol.Vec camera,
      Matrix4fc viewProjection,
      int screenWidth,
      int screenHeight,
      int barWidth,
      int barHeight,
      boolean showNumbers) {
    if (screenWidth < barWidth + 8 || screenHeight < barHeight + 24) return null;
    var relative = ProxyView.relative(head, camera);
    var clip = viewProjection.transform(new Vector4f(
        (float) relative.x(), (float) relative.y(), (float) relative.z(), 1));
    if (!clip.isFinite() || clip.w <= .05f) return null;
    double nx = clip.x / clip.w, ny = clip.y / clip.w;
    if (Math.abs(nx) > 1 || Math.abs(ny) > 1) return null;
    int x = (int) Math.round((nx + 1) * screenWidth / 2);
    int y = (int) Math.round((1 - ny) * screenHeight / 2) - barHeight - 3;
    if (y < (showNumbers ? 14 : 4) || y + barHeight > screenHeight - 4) return null;
    x = Math.clamp(x - barWidth / 2, 4, screenWidth - barWidth - 4);
    return new Position(x, y);
  }
}
