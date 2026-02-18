import ArgumentParser
import Hummingbird
import Foundation

@main
struct RMCDaemon: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "rmcd",
        abstract: "RMC Music Player Daemon"
    )

    @Option(name: .long, help: "Port to listen on")
    var port: Int = 18895

    @Option(name: .long, help: "Host to bind to")
    var host: String = "127.0.0.1"

    func run() async throws {
        let startTime = Date()
        let controller = MusicController()
        let library = MusicKitLibrary()
        let authManager = AuthorizationManager()

        let router = buildRouter(
            controller: controller,
            library: library,
            authManager: authManager,
            startTime: startTime
        )
        let app = Application(router: router, configuration: .init(address: .hostname(host, port: port)))

        print("rmcd v0.1.0 listening on \(host):\(port)")

        try await app.run()
    }
}
