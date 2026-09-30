import Foundation
import Network

/// Actor-based controller for Marantz NR1510 receiver via telnet
actor MarantzReceiverController {
    private let hostname: String
    private let port: UInt16 = 23
    private let timeout: TimeInterval = 2.0  // Reduced from 5.0 for faster failure
    private var lastCommandTime: Date = .distantPast
    private let minCommandInterval: TimeInterval = 0.1  // 100ms between commands

    init(hostname: String) {
        self.hostname = hostname
    }

    // MARK: - Connection Management

    /// Send one command over a fresh connection.
    ///
    /// Queries ("MV?") are answered, but set commands only get a reply when
    /// they change something - setting the volume the receiver is already at
    /// gets none - so set commands don't wait for one.
    ///
    /// A query that times out is retried once: the receiver is sometimes slow
    /// to accept a connection (from standby, or the daemon's first one). Set
    /// commands aren't retried, so a step like MVUP is never sent twice.
    private func sendCommand(_ command: String, expectReply: Bool = true) async throws -> String? {
        do {
            return try await sendCommandOnce(command, expectReply: expectReply)
        } catch MarantzError.timeout where expectReply {
            return try await sendCommandOnce(command, expectReply: expectReply)
        }
    }

    private func sendCommandOnce(_ command: String, expectReply: Bool) async throws -> String? {
        // Rate limiting: wait if last command was too recent
        let now = Date()
        let timeSinceLastCommand = now.timeIntervalSince(lastCommandTime)
        if timeSinceLastCommand < minCommandInterval {
            let waitTime = minCommandInterval - timeSinceLastCommand
            try await Task.sleep(nanoseconds: UInt64(waitTime * 1_000_000_000))
        }
        lastCommandTime = Date()

        let host = NWEndpoint.Host(hostname)
        let port = NWEndpoint.Port(rawValue: self.port)!
        let connection = NWConnection(host: host, port: port, using: .tcp)

        return try await withCheckedThrowingContinuation { continuation in
            var hasReturned = false

            // Timeout task
            let timeoutTask = Task {
                try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                if !hasReturned {
                    hasReturned = true
                    connection.cancel()
                    continuation.resume(throwing: MarantzError.timeout)
                }
            }

            connection.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    // Send command
                    let commandData = (command + "\r").data(using: .ascii)!
                    connection.send(content: commandData, completion: .contentProcessed { sendError in
                        if let sendError = sendError, !hasReturned {
                            hasReturned = true
                            timeoutTask.cancel()
                            connection.cancel()
                            continuation.resume(throwing: MarantzError.connectionFailed(sendError.localizedDescription))
                            return
                        }

                        if !expectReply {
                            if !hasReturned {
                                hasReturned = true
                                timeoutTask.cancel()
                                connection.cancel()
                                continuation.resume(returning: nil)
                            }
                            return
                        }

                        // Receive response
                        connection.receive(minimumIncompleteLength: 1, maximumLength: 1024) { data, _, isComplete, receiveError in
                            if hasReturned {
                                return
                            }

                            if let receiveError = receiveError {
                                hasReturned = true
                                timeoutTask.cancel()
                                connection.cancel()
                                continuation.resume(throwing: MarantzError.connectionFailed(receiveError.localizedDescription))
                                return
                            }

                            if let data = data, let response = String(data: data, encoding: .ascii) {
                                let trimmed = response.trimmingCharacters(in: .whitespacesAndNewlines)
                                hasReturned = true
                                timeoutTask.cancel()
                                connection.cancel()
                                continuation.resume(returning: trimmed.isEmpty ? nil : trimmed)
                                return
                            }

                            if isComplete {
                                hasReturned = true
                                timeoutTask.cancel()
                                connection.cancel()
                                continuation.resume(returning: nil)
                                return
                            }
                        }
                    })

                case .failed(let error):
                    if !hasReturned {
                        hasReturned = true
                        timeoutTask.cancel()
                        connection.cancel()
                        continuation.resume(throwing: MarantzError.connectionFailed(error.localizedDescription))
                    }

                case .waiting(let error):
                    if !hasReturned {
                        hasReturned = true
                        timeoutTask.cancel()
                        connection.cancel()
                        continuation.resume(throwing: MarantzError.connectionFailed(error.localizedDescription))
                    }

                default:
                    break
                }
            }

            connection.start(queue: .global())
        }
    }

    // MARK: - Power and Input

    /// Power the main zone on and select `input` (e.g. "MPLAY"), leaving
    /// alone whatever is already right, so a call when the receiver is on
    /// and on that input is just two quick queries.
    func wake(input: String?) async throws {
        if !Self.reply(try await sendCommand("ZM?"), has: "ZMON") {
            _ = try await sendCommand("ZMON", expectReply: false)
            // The receiver ignores commands for a moment while powering up.
            try await Task.sleep(nanoseconds: 2_000_000_000)
        }
        guard let input, !input.isEmpty else { return }
        // Just after power-on the receiver ignores input changes (and floods
        // status lines) for a few seconds, so keep checking until it reports
        // the input rather than sending the command once.
        for _ in 0..<6 {
            if Self.reply(try? await sendCommand("SI?"), has: "SI\(input)") { return }
            _ = try await sendCommand("SI\(input)", expectReply: false)
            try await Task.sleep(nanoseconds: 1_500_000_000)
        }
        throw MarantzError.invalidResponse("Receiver did not switch to input \(input)")
    }

    /// Replies can carry several status lines ("SIMPLAY\rSVOFF").
    private static func reply(_ response: String?, has status: String) -> Bool {
        (response ?? "").split(whereSeparator: \.isWhitespace).contains { $0 == status }
    }

    // MARK: - Volume Control

    /// Set receiver volume (0-100 scale, mapped to Marantz 0-98)
    func setVolume(_ apiLevel: Int) async throws {
        let clamped = max(0, min(100, apiLevel))
        let marantzLevel = Int(Double(clamped) * 0.98)
        _ = try await sendCommand("MV\(marantzLevel)", expectReply: false)
    }

    /// Increase volume by one step
    func volumeUp() async throws {
        _ = try await sendCommand("MVUP", expectReply: false)
    }

    /// Decrease volume by one step
    func volumeDown() async throws {
        _ = try await sendCommand("MVDOWN", expectReply: false)
    }

    /// Get current receiver volume (returns 0-100 scale)
    func getVolume() async throws -> Int {
        guard let response = try await sendCommand("MV?") else {
            throw MarantzError.noResponse
        }

        // Parse response like "MV30" or "MV395" (39.5)
        let digits = response.filter { $0.isNumber }
        guard let marantzVolume = Int(digits) else {
            throw MarantzError.invalidResponse("Could not parse volume: \(response)")
        }

        // Convert from Marantz 0-98 scale to API 0-100 scale
        let apiVolume = Int(Double(marantzVolume) / 0.98)
        return min(100, apiVolume)
    }
}

// MARK: - Error Types

enum MarantzError: Error, LocalizedError {
    case connectionFailed(String)
    case timeout
    case noResponse
    case invalidResponse(String)

    var errorDescription: String? {
        switch self {
        case .connectionFailed(let message):
            return "Receiver connection failed: \(message)"
        case .timeout:
            return "Receiver connection timed out (check if receiver is online)"
        case .noResponse:
            return "Receiver did not respond to command"
        case .invalidResponse(let message):
            return "Invalid receiver response: \(message)"
        }
    }
}
