package dev.eldencraft.bridge.client;

import java.util.Locale;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.Difficulty;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;

/**
 * Creates or opens the dedicated world once Minecraft reaches its initial title screen. Returning
 * to the title screen after playing or cancelling a load is respected.
 */
public final class EldenCraftWorld {
  public static final String NAME = "EldenCraft";
  private static final String LEGACY_NAME = "EldenCraft Passthrough Lab";
  private static final org.slf4j.Logger LOG =
      org.slf4j.LoggerFactory.getLogger("eldencraft_bridge");
  private static final Startup STARTUP =
      new Startup(
          System.getenv("ELDENCRAFT_AUTO_WORLD"),
          System.getenv("ELDENCRAFT_CREATE_WORLD"),
          System.getenv("ELDENCRAFT_WORLD_PROFILE"));

  private EldenCraftWorld() {}

  static boolean supportedName(String name) {
    return NAME.equals(name)
        || LEGACY_NAME.equals(name)
        || (name != null && name.matches("EldenCraft - [a-z0-9][a-z0-9_-]{0,39}"));
  }

  static String profileFolder(String profile) {
    if (profile == null || profile.isBlank()) return NAME;
    String key = profile.trim().toLowerCase(Locale.ROOT);
    if (!key.matches("[a-z0-9][a-z0-9_-]{0,39}"))
      throw new IllegalArgumentException("Invalid EldenCraft world profile: " + profile);
    return key.equals("default") ? NAME : NAME + " - " + key;
  }

  interface Worlds {
    boolean exists(String folder);

    void open(String folder);

    void create(String folder);
  }

  static final class Startup {
    private final boolean disabled, create;
    private final String folder;
    private boolean attempted;

    Startup(String automatic, String creation) {
      this(automatic, creation, null);
    }

    Startup(String automatic, String creation, String profile) {
      disabled = "0".equals(automatic);
      create = !"0".equals(creation);
      folder = profileFolder(profile);
    }

    void tick(boolean titleReady, boolean inWorld, Worlds worlds) {
      if (attempted || disabled) return;
      if (inWorld) {
        attempted = true;
        return;
      }
      if (!titleReady) return;
      // Consume startup before handing control to vanilla's asynchronous world-loading screens.
      attempted = true;
      if (worlds.exists(folder)) {
        worlds.open(folder);
      } else if (folder.equals(NAME) && worlds.exists(LEGACY_NAME)) {
        worlds.open(LEGACY_NAME);
      } else if (create) {
        worlds.create(folder);
      } else {
        LOG.warn("World '{}' is missing and automatic creation is disabled.", folder);
      }
    }
  }

  static LevelSettings settings() {
    return settings(NAME);
  }

  static LevelSettings settings(String folder) {
    return new LevelSettings(
        folder,
        GameType.SURVIVAL,
        new LevelSettings.DifficultySettings(Difficulty.NORMAL, false, false),
        true,
        WorldDataConfiguration.DEFAULT);
  }

  static WorldOptions options() {
    return WorldOptions.defaultWithRandomSeed().withStructures(false);
  }

  public static void tick(Minecraft client) {
    if (STARTUP.attempted || STARTUP.disabled) return;
    STARTUP.tick(
        client.gui.screen() instanceof TitleScreen && client.gui.overlay() == null,
        client.level != null || client.getSingleplayerServer() != null,
        new Worlds() {
          @Override
          public boolean exists(String folder) {
            return client.getLevelSource().levelExists(folder);
          }

          @Override
          public void open(String folder) {
            LOG.info("Opening the dedicated '{}' world.", folder);
            client
                .createWorldOpenFlows()
                .openWorld(folder, () -> LOG.info("Auto-open of {} was cancelled.", folder));
          }

          @Override
          public void create(String folder) {
            LOG.info("Creating and opening the dedicated '{}' survival world.", folder);
            client
                .createWorldOpenFlows()
                .createFreshLevel(
                    folder,
                    settings(folder),
                    options(),
                    registries ->
                        registries
                            .lookupOrThrow(Registries.WORLD_PRESET)
                            .getOrThrow(WorldPresets.FLAT)
                            .value()
                            .createWorldDimensions(),
                    client.gui.screen());
          }
        });
  }
}
