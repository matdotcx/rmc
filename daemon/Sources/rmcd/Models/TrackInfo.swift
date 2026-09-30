import Foundation

struct TrackInfo: Codable, Sendable {
    let name: String
    let artist: String
    let album: String
    let duration: Double
    let position: Double
    let albumArtist: String
    /// MusicKit library ID — the only reliable way to play this exact track.
    var id: String? = nil
    var trackNumber: Int? = nil
    var discNumber: Int? = nil

    enum CodingKeys: String, CodingKey {
        case name, artist, album, duration, position, id
        case albumArtist = "album_artist"
        case trackNumber = "track_number"
        case discNumber = "disc_number"
    }
}
