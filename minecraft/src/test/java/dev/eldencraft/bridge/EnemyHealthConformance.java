package dev.eldencraft.bridge;

import com.google.gson.JsonParser;
import java.io.IOException;
import java.util.List;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/** Independent screen-space expectations across camera headings, pitches and GUI scales. */
public final class EnemyHealthConformance {
  private static int checks;

  private static void check(boolean result, String message) {
    checks++;
    if (!result) throw new AssertionError(message);
  }

  private static ProxyProtocol.Target target(int flags, float hp, float maxHp) {
    return new ProxyProtocol.Target(5, 7, new ProxyProtocol.Vec(-.5, 0, 9.5),
        new ProxyProtocol.Vec(.5, 2, 10.5), hp, maxHp, flags, 1);
  }

  public static void main(String[] args) throws Exception {
    var enemy = target(3, 50, 100);
    check(EnemyHealthDisplay.visible(enemy, 16), "living nearby enemy is visible");
    check(!EnemyHealthDisplay.visible(enemy, 8), "far enemies respect range");
    check(!EnemyHealthDisplay.visible(target(0, 50, 100), 16), "native LOS failure hides bar");
    check(!EnemyHealthDisplay.visible(target(1, 50, 100), 16), "unready targets hide bar");
    check(!EnemyHealthDisplay.visible(target(3, 0, 100), 16), "dead enemies hide bar");
    check(!EnemyHealthDisplay.visible(target(3, Float.NaN, 100), 16), "invalid health hides bar");
    check(!EnemyHealthDisplay.visible(target(3, 101, 100), 16), "invalid fraction rejected");
    check(!EnemyHealthDisplay.visible(target(3, 50, 0), 16), "invalid capacity rejected");
    var head = EnemyHealthDisplay.head(enemy, .35);
    check(Math.abs(head.y() - 2.35) < 1e-9 && head.x() == 0 && head.z() == 10,
        "head anchor uses top of enemy body with clearance");
    var giant = new ProxyProtocol.Target(9, 1, new ProxyProtocol.Vec(-30, 0, 2),
        new ProxyProtocol.Vec(30, 40, 62), 40000, 40000, 3, 1);
    check(EnemyHealthDisplay.visible(giant, 4), "nearby giant not culled by its distant centre");
    check(EnemyHealthDisplay.head(giant, .35).y() > 40, "giant bar uses authored height");
    var frame = new ProxyProtocol.Frame(10, 1000, 12, 3, 45, 60,
        new ProxyProtocol.Vec(0, 1.6, 0), new ProxyProtocol.Vec(0, 0, 1),
        0, 0, 16, 36, 22, 0, 0, List.of(enemy));
    check(EnemyHealthDisplay.sameContext(frame, 12, 60, 249_999_999L), "fresh same host/map");
    check(!EnemyHealthDisplay.sameContext(frame, 12, 60, 250_000_000L), "expiry boundary");
    check(!EnemyHealthDisplay.sameContext(frame, 12, 60, -1), "clock reversal rejected");
    check(!EnemyHealthDisplay.sameContext(frame, 13, 60, 0), "different process rejected");
    check(!EnemyHealthDisplay.sameContext(frame, 12, 61, 0), "different map rejected");
    check(!EnemyHealthDisplay.sameContext(null, 12, 60, 0), "disconnected host rejected");

    for (double yaw : new double[] {-180, -90, 0, 45, 90, 179})
      for (double pitch : new double[] {-65, 0, 65})
        for (int[] size : new int[][] {{854, 480}, {1920, 1080}, {640, 480}, {960, 540}}) {
          double a = Math.toRadians(yaw), b = Math.toRadians(pitch);
          var forward = new Vector3f((float) (-Math.sin(a) * Math.cos(b)),
              (float) -Math.sin(b), (float) (Math.cos(a) * Math.cos(b)));
          var right = new Vector3f(0, 1, 0).cross(forward).normalize();
          var up = new Vector3f(forward).cross(right).normalize();
          var camera = new ProxyProtocol.Vec(7, 3, -2);
          var lens = new Matrix4f().perspective((float) Math.toRadians(70),
              (float) size[0] / size[1], .05f, 2048, true);
          var projection = lens.mul(ProxyView.rotation(
              new ProxyProtocol.Vec(forward.x, forward.y, forward.z)));
          var point = new Vector3f(forward).mul(10).add(new Vector3f(right).mul(1.25f))
              .add(new Vector3f(up).mul(.5f));
          var anchor = new ProxyProtocol.Vec(camera.x() + point.x,
              camera.y() + point.y, camera.z() + point.z);
          var screen = EnemyHealthDisplay.project(anchor, camera, projection,
              size[0], size[1], 88, 7, true);
          double tangent = Math.tan(Math.toRadians(35));
          int expectedX = (int) Math.round(size[0] / 2d + 1.25 * size[1] / (20 * tangent)) - 44;
          int expectedY = (int) Math.round(size[1] / 2d - .5 * size[1] / (20 * tangent)) - 10;
          check(screen != null && Math.abs(screen.x() - expectedX) <= 1
              && Math.abs(screen.y() - expectedY) <= 1, "head stays aligned to host camera");
          var behind = new ProxyProtocol.Vec(camera.x() - forward.x * 10,
              camera.y() - forward.y * 10, camera.z() - forward.z * 10);
          check(EnemyHealthDisplay.project(behind, camera, projection, size[0], size[1], 88, 7,
              true) == null, "behind-camera enemy hidden, including front F5 view");
        }
    var lens = new Matrix4f().perspective((float) Math.toRadians(70), 16f / 9, .05f, 2048, true)
        .mul(ProxyView.rotation(new ProxyProtocol.Vec(0, 0, 1)));
    var zero = new ProxyProtocol.Vec(0, 0, 0);
    for (var offscreen : new ProxyProtocol.Vec[] {new ProxyProtocol.Vec(30, 0, 10),
        new ProxyProtocol.Vec(0, 30, 10), new ProxyProtocol.Vec(0, 0, 0),
        new ProxyProtocol.Vec(Double.NaN, 0, 10)})
      check(EnemyHealthDisplay.project(offscreen, zero, lens, 1920, 1080, 88, 7, true) == null,
          "off-screen or invalid anchors hidden");
    check(EnemyHealthDisplay.project(head, zero, lens, 40, 40, 88, 7, true) == null,
        "tiny viewport cannot overflow");
    var defaults = CampaignHudConfig.parse(JsonParser.parseString("{}").getAsJsonObject());
    check(defaults.enemyBar().enabled() && defaults.enemyBar().width() == 88
        && defaults.enemyBar().showNumbers(), "old campaign files enable head bars");
    var parsed = CampaignHudConfig.parse(JsonParser.parseString(
        "{\"hud\":{\"enemyBar\":{\"enabled\":false,\"width\":120,\"headOffset\":0.8}}}")
        .getAsJsonObject());
    check(!parsed.enemyBar().enabled() && parsed.enemyBar().width() == 120
        && parsed.enemyBar().headOffset() == .8, "configuration overrides parsed");
    for (String invalid : List.of("{\"width\":1}", "{\"height\":2}",
        "{\"headOffset\":-1}", "{\"maxDistance\":1000}", "{\"showNumbers\":1}")) {
      try {
        CampaignHudConfig.parse(JsonParser.parseString("{\"hud\":{\"enemyBar\":" + invalid + "}}")
            .getAsJsonObject());
        throw new AssertionError("invalid head bar configuration accepted");
      } catch (IOException expected) {
        checks++;
      }
    }
    System.out.println("Enemy health conformance: " + checks + " checks passed (no live render claim).");
  }
}
