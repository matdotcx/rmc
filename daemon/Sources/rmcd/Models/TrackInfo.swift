import Foundation

struct TrackInfo: Codable, Sendable {
    let name: String
    let artist: String
    let album: String
    let duration: Double
    let position: Double
    let albumArtist: String

    enum CodingKeys: String, CodingKey {
        case name, artist, album, duration, position
        case albumArtist = "album_artist"
    }
}
