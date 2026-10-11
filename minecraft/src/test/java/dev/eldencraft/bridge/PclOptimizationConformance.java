package dev.eldencraft.bridge;

import dev.eldencraft.bridge.client.CampaignCombat;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.SharedConstants;
import net.minecraft.core.component.DataComponentInitializers.PendingComponents;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.data.registries.VanillaRegistries;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.entity.ai.attributes.*;
import net.minecraft.world.item.*;
import net.minecraft.world.item.component.ItemAttributeModifiers;

/** Real disk congestion, configurable free stamina, inventory mutation and short bow charges. */
public final class PclOptimizationConformance {
  private static int checks;

  private static void check(boolean value, String message) {
    checks++;
    if (!value) throw new AssertionError(message);
  }

  public static void main(String[] args) throws Exception {
    SharedConstants.tryDetectVersion();
    Bootstrap.bootStrap();
    BuiltInRegistries.DATA_COMPONENT_INITIALIZERS.build(VanillaRegistries.createWorldLookup())
        .forEach(PendingComponents::apply);
    var config = CampaignConfig.load(Path.of("../config/campaign-pcl.json"));
    CampaignConfig.install(config);
    var account = new CampaignStamina(config.progression.stamina(0));
    double full = account.current();
    for (String kind : List.of("sword", "axe", "spear", "mace", "bow", "crossbow", "other")) {
      check(config.stamina.cost(kind) == 0, "free configured action " + kind);
      for (int i = 0; i < 1000; i++) check(account.spend(config.stamina.cost(kind)), "action permitted");
    }
    check(!account.guard(100000, 1000, config.stamina), "repeated hits cannot break free guard");
    check(account.current() == full && account.guardReady(), "stamina remains full");
    check(CampaignStamina.absorbed(full, 100000, config.stamina) == 1, "free guard absorbs whole hit");
    check(!config.hud.stamina().enabled(), "stamina HUD remains hidden");

    var scroll = new HostScrollInput();
    scroll.reset(10);
    scroll.observe(11, 1);
    scroll.observe(11, 1);
    scroll.observe(12, 0);
    check(scroll.take() == 1, "wheel survives the following zero frame, once only");
    check(scroll.take() == 0, "next tick cannot replay wheel");
    for (int i = 13; i < 113; i++) scroll.observe(i, -1);
    check(scroll.take() == -1, "rapid scrolling reaches final hotbar slot without a backlog");
    scroll.observe(113, 2);
    scroll.reset(114);
    check(scroll.take() == 0, "menu/focus/context handoff discards pending world scroll");

    check(CampaignBowCharge.power(0, BowItem.getPowerForTime(0)) < .1f, "zero draw cannot invent a shot");
    for (int ticks = 1; ticks < 20; ticks++) {
      float vanilla = BowItem.getPowerForTime(ticks);
      float shot = CampaignBowCharge.power(ticks, vanilla);
      check(shot >= .1f && shot < 1, "partial draw launches a weaker arrow at " + ticks);
      if (vanilla >= .1f) check(shot == vanilla, "ordinary partial draw keeps vanilla speed");
    }
    check(CampaignBowCharge.power(20, BowItem.getPowerForTime(20)) == 1, "full draw preserved");
    var stack = new ItemStack(Items.IRON_SWORD);
    CampaignCombat.tune(stack);
    var attributes = stack.get(DataComponents.ATTRIBUTE_MODIFIERS);
    for (int i = 0; i < 5000; i++) CampaignCombat.tune(stack);
    check(stack.get(DataComponents.ATTRIBUTE_MODIFIERS) == attributes, "stable item keeps same component");
    stack.set(DataComponents.ATTRIBUTE_MODIFIERS, ItemAttributeModifiers.EMPTY);
    CampaignCombat.tune(stack);
    check(stack.get(DataComponents.ATTRIBUTE_MODIFIERS).equals(attributes), "external component change invalidates cache");
    var changed = config.raw();
    changed.getAsJsonObject("weapons").getAsJsonObject("minecraft:iron_sword").addProperty("damage", 33);
    CampaignConfig.install(CampaignConfig.parse(changed));
    CampaignCombat.tune(stack);
    check(!stack.get(DataComponents.ATTRIBUTE_MODIFIERS).equals(attributes), "config reload invalidates cache");

    Path folder = Files.createTempDirectory("eldencraft-pcl-conformance-");
    var entered = new CountDownLatch(1);
    var release = new CountDownLatch(1);
    var finalWritten = new CountDownLatch(1);
    var writes = new AtomicInteger();
    var attempts = new AtomicInteger();
    var history = Collections.synchronizedList(new ArrayList<String>());
    try (var publisher = new LatestStatePublisher("test-state", (target, payload) -> {
      if (attempts.getAndIncrement() == 0) {
        entered.countDown();
        try { release.await(2, TimeUnit.SECONDS); }
        catch (InterruptedException e) { throw new java.io.IOException(e); }
        throw new java.io.IOException("simulated Windows sharing violation");
      }
      LatestStatePublisher.writeAtomic(target, payload);
      history.add(payload);
      writes.incrementAndGet();
      if (payload.equals("newest")) finalWritten.countDown();
    })) {
      Path target = folder.resolve("state.json");
      publisher.offer(target, "first", 250);
      check(entered.await(1, TimeUnit.SECONDS), "writer can block independently");
      long start = System.nanoTime();
      for (int i = 0; i < 10000; i++) publisher.offer(target, "queued-" + i, 250);
      publisher.offer(target, "newest", 250);
      long elapsed = System.nanoTime() - start;
      check(elapsed < 500_000_000L, "enqueue cannot wait on the blocked writer");
      System.out.println("Queued 10000 live states in " + elapsed / 1_000_000.0 + " ms while disk writer was blocked");
      release.countDown();
      check(finalWritten.await(2, TimeUnit.SECONDS), "sharing violation recovers using newest state");
      check(Files.readString(target).equals("newest"), "reader sees coherent newest payload");
      check(writes.get() == 1 && history.equals(List.of("newest")), "congestion coalesces old snapshots");
    } finally {
      release.countDown();
      Files.deleteIfExists(folder.resolve("state.json"));
      Files.deleteIfExists(folder.resolve("state.json.pcl-state.tmp"));
      Files.delete(folder);
    }
    var waiting = new CountDownLatch(1);
    var unblock = new CountDownLatch(1);
    var firstDone = new CountDownLatch(1);
    var staleWrites = new AtomicInteger();
    try (var publisher = new LatestStatePublisher("test-expiry", (target, payload) -> {
      if (payload.equals("blocking")) {
        waiting.countDown();
        try { unblock.await(1, TimeUnit.SECONDS); }
        catch (InterruptedException e) { throw new java.io.IOException(e); }
        firstDone.countDown();
      } else staleWrites.incrementAndGet();
    })) {
      publisher.offer(Path.of("blocking"), "blocking", 250);
      check(waiting.await(1, TimeUnit.SECONDS), "expiry test holds writer");
      publisher.offer(Path.of("expired"), "expired", 10);
      Thread.sleep(40);
      unblock.countDown();
      check(firstDone.await(1, TimeUnit.SECONDS), "writer resumes after deadline");
      Thread.sleep(40);
      check(staleWrites.get() == 0, "stale queue entries never publish or renew input authorization");
    } finally {
      unblock.countDown();
    }
    System.out.println("PCL optimization conformance: " + checks + " checks passed");
  }
}
