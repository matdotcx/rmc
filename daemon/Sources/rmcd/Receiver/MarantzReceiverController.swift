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

    private func sendCommand(_ command: String) async throws -> String? {
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

    // MARK: - Volume Control

    /// Set receiver volume (0-100 scale, mapped to Marantz 0-98)
    func setVolume(_ apiLevel: Int) async throws {
        let clamped = max(0, min(100, apiLevel))
        let marantzLevel = Int(Double(clamped) * 0.98)
        _ = try await sendCommand("MV\(marantzLevel)")
    }

    /// Increase volume by one step
    func volumeUp() async throws {
        _ = try await sendCommand("MVUP")
    }

    /// Decrease volume by one step
    func volumeDown() async throws {
        _ = try await sendCommand("MVDOWN")
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
