import Foundation
import MusicKit
import ScriptingBridge

actor MusicController {

    private let player = ApplicationMusicPlayer.shared
    private let app: MusicApplication

    init() {
        let sbApp = SBApplication(bundleIdentifier: "com.apple.Music")!
        self.app = sbApp as MusicApplication
    }

    // MARK: - Playback Control

    func play() async throws {
        try await player.play()
    }

    func pause() {
        player.pause()
    }

    func playpause() async throws {
        if player.state.playbackStatus == .playing {
            player.pause()
        } else {
            try await player.play()
        }
    }

    func nextTrack() async throws {
        try await player.skipToNextEntry()
    }

    func previousTrack() async throws {
        try await player.skipToPreviousEntry()
    }

    // MARK: - Player State

    func getPlayerState() -> String {
        switch player.state.playbackStatus {
        case .playing: return "playing"
        case .paused:  return "paused"
        default:       return "stopped"
        }
    }

    // Cache metadata so we only query the library when the track changes
    private var _cachedEntryID: MusicPlayer.Queue.Entry.ID?
    private var _cachedName: String = ""
    private var _cachedArtist: String = ""
    private var _cachedAlbum: String = ""
    private var _cachedDuration: Double = 0
    private var _cachedAlbumArtist: String = ""

    func getCurrentTrack() async -> TrackInfo? {
        let status = player.state.playbackStatus
        guard status == .playing || status == .paused else {
            _cachedEntryID = nil
            return nil
        }

        guard let entry = player.queue.currentEntry else { return nil }
        let position = player.playbackTime

        // Reuse cached metadata if same queue entry
        if entry.id == _cachedEntryID {
            return TrackInfo(
                name: _cachedName, artist: _cachedArtist, album: _cachedAlbum,
                duration: _cachedDuration, position: position, albumArtist: _cachedAlbumArtist
            )
        }

        // New entry — resolve full metadata from library
        let title = entry.title
        let subtitle = entry.subtitle ?? ""

        var name = title
        var artist = subtitle
        var album = ""
        var duration: Double = 0
        var albumArtist = subtitle

        var request = MusicLibraryRequest<Song>()
        request.filter(matching: \.title, equalTo: title)
        if !subtitle.isEmpty {
            request.filter(matching: \.artistName, equalTo: subtitle)
        }
        if let response = try? await request.response(),
           let song = response.items.first {
            name = song.title
            artist = song.artistName
            album = song.albumTitle ?? ""
            duration = song.duration ?? 0
            albumArtist = song.artistName
        }

        _cachedEntryID = entry.id
        _cachedName = name
        _cachedArtist = artist
        _cachedAlbum = album
        _cachedDuration = duration
        _cachedAlbumArtist = albumArtist

        return TrackInfo(
            name: name, artist: artist, album: album,
            duration: duration, position: position, albumArtist: albumArtist
        )
    }

    // MARK: - Volume (ScriptingBridge)

    func getVolume() -> Int {
        return app.soundVolume ?? 50
    }

    func setVolume(_ level: Int) {
        let clamped = max(0, min(100, level))
        (app as? SBApplication)?.setValue(clamped, forKey: "soundVolume")
    }

    // MARK: - Shuffle (MusicKit)

    func getShuffle() -> Bool {
        return player.state.shuffleMode == .songs
    }

    func setShuffle(_ enabled: Bool) {
        player.state.shuffleMode = enabled ? .songs : .off
    }

    // MARK: - Repeat (MusicKit)

    func getRepeat() -> String {
        switch player.state.repeatMode {
        case .one: return "one"
        case .all: return "all"
        default:   return "off"
        }
    }

    func setRepeat(_ mode: String) {
        switch mode {
        case "one": player.state.repeatMode = .one
        case "all": player.state.repeatMode = .all
        default:    player.state.repeatMode = MusicPlayer.RepeatMode.none
        }
    }

    // MARK: - Seek

    func setPlayerPosition(_ position: Double) {
        player.playbackTime = position
    }

    // MARK: - Play Track (MusicKit queue)

    func playTrack(name: String, artist: String?) async throws {
        var request = MusicLibraryRequest<Song>()
        request.filter(matching: \.title, equalTo: name)
        if let artist, !artist.isEmpty, artist != "Unknown Artist" {
            request.filter(matching: \.artistName, equalTo: artist)
        }
        let response = try await request.response()

        if let song = response.items.first {
            try await playWithAlbumContext(song)
            return
        }

        // Fallback: name-only search if artist filter excluded results
        if artist != nil {
            var fallback = MusicLibraryRequest<Song>()
            fallback.filter(matching: \.title, equalTo: name)
            let fallbackResponse = try await fallback.response()
            if let song = fallbackResponse.items.first {
                try await playWithAlbumContext(song)
                return
            }
        }

        throw MusicControllerError.trackNotFound("Track '\(name)' not found")
    }

    /// Queue the song within its album so next/prev and auto-advance work.
    private func playWithAlbumContext(_ song: Song) async throws {
        if let albumTitle = song.albumTitle {
            var albumRequest = MusicLibraryRequest<Song>()
            albumRequest.filter(matching: \.albumTitle, equalTo: albumTitle)
            albumRequest.filter(matching: \.artistName, equalTo: song.artistName)
            albumRequest.sort(by: \.trackNumber, ascending: true)
            let albumResponse = try await albumRequest.response()

            if albumResponse.items.count > 1 {
                player.queue = ApplicationMusicPlayer.Queue(for: albumResponse.items, startingAt: song)
                try await player.play()
                return
            }
        }

        player.queue = ApplicationMusicPlayer.Queue(for: [song])
        try await player.play()
    }

    // MARK: - Play Playlist (MusicKit queue)

    func playPlaylist(name: String) async throws {
        var request = MusicLibraryRequest<Playlist>()
        request.filter(matching: \.name, equalTo: name)
        let response = try await request.response()

        guard let playlist = response.items.first else {
            throw MusicControllerError.trackNotFound("Playlist '\(name)' not found")
        }

        let detailed = try await playlist.with(.tracks)
        guard let tracks = detailed.tracks, !tracks.isEmpty else {
            throw MusicControllerError.trackNotFound("Playlist '\(name)' has no tracks")
        }

        player.queue = ApplicationMusicPlayer.Queue(for: tracks)
        try await player.play()
    }

    // MARK: - Combined Status

    func getStatus() async -> StatusResponse {
        let state = getPlayerState()
        let volume = getVolume()
        let shuffle = getShuffle()
        let repeatMode = getRepeat()
        let track = await getCurrentTrack()

        return StatusResponse(
            state: state,
            track: track,
            volume: volume,
            shuffle: shuffle,
            repeatMode: repeatMode
        )
    }
}

enum MusicControllerError: Error, LocalizedError {
    case trackNotFound(String)

    var errorDescription: String? {
        switch self {
        case .trackNotFound(let msg): return msg
        }
    }
}
