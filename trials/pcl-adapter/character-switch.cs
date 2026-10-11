using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

namespace EldenCraftPcl {
    // Tracks physical key edges even outside the game. Alt-tab with F8 held
    // cannot become a fresh press; neither hold nor ACK delay queues toggles.
    public sealed class SwitchEdge {
        private bool previous;
        private long last = long.MinValue;
        public bool Poll(bool foreground, bool down, bool pending, long now) {
            bool edge = down && !previous;
            previous = down;
            if (!foreground || !edge || pending || (last != long.MinValue && now - last < 500)) return false;
            last = now;
            return true;
        }
    }

    public sealed class SwitchCommand {
        public ulong seq { get; set; }
        public string action { get; set; }
    }
    public sealed class SwitchAck {
        public ulong seq { get; set; }
        public string status { get; set; }
    }

    public static class CharacterSwitch {
        [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int key);
        [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint process);

        public static ulong NextSequence(string current, ulong previous) {
            var serializer = new JavaScriptSerializer();
            if (!string.IsNullOrWhiteSpace(current)) {
                var old = serializer.Deserialize<SwitchCommand>(current);
                previous = Math.Max(previous, old.seq);
            }
            if (previous == ulong.MaxValue) throw new InvalidOperationException("Control sequence exhausted");
            return Math.Max(previous + 1, (ulong)DateTime.UtcNow.Ticks);
        }

        public static void Publish(string path, ulong sequence) {
            var command = new SwitchCommand { seq = sequence, action = "toggle_build" };
            string temporary = path + ".pcl-" + Process.GetCurrentProcess().Id + ".tmp";
            try {
                File.WriteAllText(temporary, new JavaScriptSerializer().Serialize(command), new UTF8Encoding(false));
                if (File.Exists(path)) File.Replace(temporary, path, null);
                else File.Move(temporary, path);
            } finally {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }

        public static void Run(int gameProcessId, string directory) {
            var game = Process.GetProcessById(gameProcessId);
            if (!string.Equals(game.ProcessName, "eldenring", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Target must be Elden Ring");
            if (!Path.IsPathRooted(directory) || !Directory.Exists(directory)) throw new InvalidOperationException("Runtime data directory missing");
            bool ownsMutex;
            using (var mutex = new Mutex(true, "Local\\EldenCraftPclSwitch-" + gameProcessId, out ownsMutex)) {
                if (!ownsMutex) return;
                try {
                    RunLoop(game, directory);
                } finally { mutex.ReleaseMutex(); }
            }
        }

        private static void RunLoop(Process game, string directory) {
            string command = Path.Combine(directory, "command.json");
            string ackPath = Path.Combine(directory, "command-ack.json");
            string logfile = Path.Combine(directory, "pcl-character-switch.log");
            var serializer = new JavaScriptSerializer();
            var clock = Stopwatch.StartNew();
            var edge = new SwitchEdge();
            edge.Poll(false, GetAsyncKeyState(0x77) < 0, false, 0);
            ulong sequence = 0, pending = 0;
            long sentAt = 0;
            Action<string> log = text => File.AppendAllText(logfile, DateTime.Now.ToString("s") + " " + text + Environment.NewLine);
            log("F8 character switch ready for Elden Ring PID " + game.Id + ". Uses native reversible toggle_build; no injected input or memory writes.");
            while (!game.HasExited) {
                uint foreground;
                GetWindowThreadProcessId(GetForegroundWindow(), out foreground);
                bool down = GetAsyncKeyState(0x77) < 0; // F8
                if (pending != 0) {
                    if (File.Exists(ackPath)) {
                        try {
                            var ack = serializer.Deserialize<SwitchAck>(File.ReadAllText(ackPath));
                            if (ack != null && ack.seq == pending) {
                                log("seq=" + pending + " " + ack.status);
                                pending = 0;
                            }
                        } catch (IOException) {} catch (ArgumentException) {}
                    }
                    if (pending != 0 && clock.ElapsedMilliseconds - sentAt > 2000) {
                        log("seq=" + pending + " acknowledgement timed out; command will not be retried. Close menus/load screens before pressing F8 again.");
                        pending = 0;
                    }
                }
                if (edge.Poll(foreground == game.Id, down, pending != 0, clock.ElapsedMilliseconds)) {
                    string current = File.Exists(command) ? File.ReadAllText(command) : null;
                    sequence = NextSequence(current, sequence);
                    Publish(command, sequence);
                    pending = sequence;
                    sentAt = clock.ElapsedMilliseconds;
                    log("seq=" + sequence + " F8 toggle requested");
                }
                Thread.Sleep(15);
            }
            log("Game exited; F8 helper stopped.");
        }
    }
}
