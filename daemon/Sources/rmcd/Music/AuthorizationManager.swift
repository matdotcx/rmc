import MusicKit

actor AuthorizationManager {

    func currentStatus() -> String {
        switch MusicAuthorization.currentStatus {
        case .authorized: return "authorized"
        case .denied: return "denied"
        case .notDetermined: return "not_determined"
        case .restricted: return "restricted"
        @unknown default: return "unknown"
        }
    }

    func requestAuthorization() async -> String {
        let status = await MusicAuthorization.request()
        switch status {
        case .authorized: return "authorized"
        case .denied: return "denied"
        case .notDetermined: return "not_determined"
        case .restricted: return "restricted"
        @unknown default: return "unknown"
        }
    }
}
