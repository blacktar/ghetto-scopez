import AppKit
import Darwin

final class HostApp: NSObject, NSApplicationDelegate {
    var item: NSStatusItem!
    var child: Process?
    var log: FileHandle?
    var stopping = false
    var termination: DispatchSourceSignal?
    let status = NSMenuItem(title: "Starting…", action: nil, keyEquivalent: "")
    func applicationDidFinishLaunching(_ notification: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        item.button?.title = "GS"
        item.button?.toolTip = "Ghetto Scopez"
        let menu = NSMenu()
        menu.addItem(status)
        for (title, selector) in [("Open Viewer", #selector(viewer)), ("Open User Guide", #selector(guide)), ("Start Server", #selector(start)), ("Stop Server", #selector(stop)), ("Show Log", #selector(showLog)), ("Quit Ghetto Scopez", #selector(quit))] {
            let entry = NSMenuItem(title: title, action: selector, keyEquivalent: "")
            entry.target = self
            menu.addItem(entry)
        }
        item.menu = menu
        signal(SIGTERM, SIG_IGN)
        termination = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
        termination?.setEventHandler { [weak self] in self?.quit() }
        termination?.resume()
        start()
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        item.button?.performClick(nil)
        return false
    }
    var logURL: URL {
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/Ghetto Scopez/host.log")
    }
    @objc func start() {
        guard child == nil else { return }
        stopping = false
        let resources = Bundle.main.resourceURL!
        do {
            try FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            if !FileManager.default.fileExists(atPath: logURL.path) {
                FileManager.default.createFile(atPath: logURL.path, contents: nil, attributes: [.posixPermissions: 0o600])
            }
            log = try FileHandle(forWritingTo: logURL)
            log?.seekToEndOfFile()
            let process = Process()
            process.executableURL = resources.appendingPathComponent("runtime/node")
            process.arguments = [resources.appendingPathComponent("host/web/server.mjs").path]
            process.currentDirectoryURL = resources.appendingPathComponent("host")
            var environment = ProcessInfo.processInfo.environment
            environment["HOST"] = "0.0.0.0"
            environment["PORT"] = "8765"
            environment["SCOPE_DIAGNOSTICS"] = "0"
            environment.removeValue(forKey: "NODE_OPTIONS")
            environment.removeValue(forKey: "NODE_PATH")
            process.environment = environment
            process.standardOutput = log
            process.standardError = log
            process.terminationHandler = { [weak self] finished in
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    self.child = nil
                    self.log?.closeFile()
                    self.log = nil
                    self.status.title = self.stopping ? "Server stopped" : "Server exited (\(finished.terminationStatus)) — see log"
                }
            }
            child = process
            try process.run()
            status.title = "Server running · port 8765"
        } catch {
            child = nil
            status.title = "Could not start server — see log"
            NSLog("Ghetto Scopez: %@", error.localizedDescription)
        }
    }
    @objc func stop() {
        stopping = true
        if let process = child, process.isRunning { process.terminate() }
        else { status.title = "Server stopped" }
    }
    @objc func viewer() { NSWorkspace.shared.open(URL(string: "http://localhost:8765/scopes.html")!) }
    @objc func guide() { NSWorkspace.shared.open(URL(string: "http://localhost:8765/guide/index.html")!) }
    @objc func showLog() { NSWorkspace.shared.open(logURL) }
    @objc func quit() { stop(); child?.waitUntilExit(); NSApplication.shared.terminate(nil) }
    func applicationWillTerminate(_ notification: Notification) { stop(); child?.waitUntilExit() }
}
// Finder alias creation runs as the logged-in user during installation, without
// starting another server or opening an application window.
if CommandLine.arguments.contains("--create-desktop-alias") {
    do {
        let target = Bundle.main.bundleURL
        let desktop = try FileManager.default.url(for: .desktopDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let output = CommandLine.arguments.count > 2 ? URL(fileURLWithPath: CommandLine.arguments[2]) : desktop.appendingPathComponent("Ghetto Scopez")
        if FileManager.default.fileExists(atPath: output.path) {
            let resolved = try URL(resolvingAliasFileAt: output, options: [.withoutUI])
            guard resolved.standardizedFileURL == target.standardizedFileURL else {
                throw NSError(domain: "GhettoScopez", code: 1, userInfo: [NSLocalizedDescriptionKey: "Desktop item already exists; it was left unchanged."])
            }
        } else {
            let bookmark = try target.bookmarkData(options: [.suitableForBookmarkFile], includingResourceValuesForKeys: nil, relativeTo: nil)
            try URL.writeBookmarkData(bookmark, to: output)
        }
        exit(0)
    } catch { fputs("Desktop shortcut: \(error.localizedDescription)\n", stderr); exit(1) }
}
let app = NSApplication.shared
let delegate = HostApp()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
