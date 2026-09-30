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
    private var _cachedID: String?

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
                duration: _cachedDuration, position: position, albumArtist: _cachedAlbumArtist,
                id: _cachedID
            )
        }

        // New entry — take metadata from the queued song itself rather than
        // re-querying the library by title, which can pick a different copy.
        var name = entry.title
        var artist = entry.subtitle ?? ""
        var album = ""
        var duration: Double = 0
        var id: String? = nil

        if case .song(let song)? = entry.item {
            name = song.title
            artist = song.artistName
            album = song.albumTitle ?? ""
            duration = song.duration ?? 0
            id = song.id.rawValue
        }
        let albumArtist = artist

        _cachedEntryID = entry.id
        _cachedName = name
        _cachedArtist = artist
        _cachedAlbum = album
        _cachedDuration = duration
        _cachedAlbumArtist = albumArtist
        _cachedID = id

        return TrackInfo(
            name: name, artist: artist, album: album,
            duration: duration, position: position, albumArtist: albumArtist, id: id
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

    // MARK: - Play Queue (MusicKit queue)

    /// Queue the given library songs in order and start playing at `start`.
    /// Songs are looked up by MusicKit ID so the exact copy chosen in the UI
    /// is played, even when the library holds several with the same title.
    func playQueue(ids: [String], start: Int) async throws {
        guard ids.indices.contains(start) else {
            throw MusicControllerError.trackNotFound("Start index \(start) out of range")
        }

        var request = MusicLibraryRequest<Song>()
        request.filter(matching: \.id, memberOf: ids.map { MusicItemID($0) })
        let response = try await request.response()

        var byID: [String: Song] = [:]
        for song in response.items { byID[song.id.rawValue] = song }

        guard let startSong = byID[ids[start]] else {
            throw MusicControllerError.trackNotFound("Track not found in library (try reindexing)")
        }
        let songs = ids.compactMap { byID[$0] }

        player.queue = ApplicationMusicPlayer.Queue(for: songs, startingAt: startSong)
        try await player.play()
    }

    // MARK: - Play Playlist (MusicKit queue)

    func playPlaylist(id: String) async throws {
        var request = MusicLibraryRequest<Playlist>()
        request.filter(matching: \.id, equalTo: MusicItemID(id))
        let response = try await request.response()

        guard let playlist = response.items.first else {
            throw MusicControllerError.trackNotFound("Playlist not found (try reindexing)")
        }

        let detailed = try await playlist.with(.tracks)
        guard let tracks = detailed.tracks, !tracks.isEmpty else {
            throw MusicControllerError.trackNotFound("Playlist '\(playlist.name)' has no tracks")
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
