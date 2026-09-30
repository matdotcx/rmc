import Foundation

struct StatusResponse: Codable, Sendable {
    let state: String
    let track: TrackInfo?
    let volume: Int
    let shuffle: Bool
    let repeatMode: String
    /// 1-based position of the current song in the play queue, and the
    /// queue's length ("3 of 14" on Now Playing).
    var queueIndex: Int? = nil
    var queueCount: Int? = nil

    enum CodingKeys: String, CodingKey {
        case state, track, volume, shuffle
        case repeatMode = "repeat"
        case queueIndex = "queue_index"
        case queueCount = "queue_count"
    }
}

struct HealthResponse: Codable, Sendable {
    let version: String
    let uptime: Double
}

struct ErrorResponse: Codable, Sendable {
    let error: String
}

struct OKResponse: Codable, Sendable {
    let ok: Bool

    init() { self.ok = true }
}

// Library response types

struct ArtistsResponse: Codable, Sendable {
    let artists: [String]
}

struct AlbumEntry: Codable, Sendable {
    let name: String
    let artist: String
}

struct AlbumsResponse: Codable, Sendable {
    let albums: [AlbumEntry]
}

struct PlaylistsResponse: Codable, Sendable {
    let playlists: [String]
}

struct TracksResponse: Codable, Sendable {
    let tracks: [TrackInfo]
}

struct AuthStatusResponse: Codable, Sendable {
    let status: String
}

struct PlaylistExport: Codable, Sendable {
    let id: String
    let name: String
    let tracks: [TrackInfo]
}

struct LibraryExportResponse: Codable, Sendable {
    let tracks: [TrackInfo]
    let playlists: [PlaylistExport]
}

// Request body types

struct SeekRequest: Codable, Sendable {
    let position: Double
}

struct PlayQueueRequest: Codable, Sendable {
    /// MusicKit library song IDs, in queue order.
    let ids: [String]
    /// Index into `ids` of the track to start playing.
    let start: Int
}

struct PlayPlaylistRequest: Codable, Sendable {
    let id: String
}

struct VolumeRequest: Codable, Sendable {
    let level: Int
}

struct ShuffleRequest: Codable, Sendable {
    let enabled: Bool
}

struct RepeatRequest: Codable, Sendable {
    let mode: String
}
