import MusicKit

actor MusicKitLibrary {

    // MARK: - Artists

    func getAllArtists() async throws -> [String] {
        var request = MusicLibraryRequest<Artist>()
        request.sort(by: \.name, ascending: true)
        let response = try await request.response()
        return response.items.map(\.name)
    }

    // MARK: - Albums

    func getAllAlbums() async throws -> [AlbumEntry] {
        var request = MusicLibraryRequest<Album>()
        request.sort(by: \.title, ascending: true)
        let response = try await request.response()
        return response.items.map { album in
            AlbumEntry(
                name: album.title,
                artist: album.artistName
            )
        }
    }

    // MARK: - Playlists

    func getPlaylists() async throws -> [String] {
        var request = MusicLibraryRequest<Playlist>()
        request.sort(by: \.name, ascending: true)
        let response = try await request.response()
        return response.items.map(\.name)
    }

    func getPlaylistTracks(name playlistName: String) async throws -> [TrackInfo] {
        var request = MusicLibraryRequest<Playlist>()
        request.filter(matching: \.name, equalTo: playlistName)
        let response = try await request.response()

        guard let playlist = response.items.first else {
            return []
        }

        let detailed = try await playlist.with(.tracks)
        guard let tracks = detailed.tracks else { return [] }

        return tracks.map { track in
            TrackInfo(
                name: track.title,
                artist: track.artistName,
                album: track.albumTitle ?? "",
                duration: track.duration ?? 0,
                position: 0,
                albumArtist: track.artistName
            )
        }
    }

    // MARK: - Tracks by Artist

    func getTracksByArtist(_ artistName: String) async throws -> [TrackInfo] {
        var request = MusicLibraryRequest<Song>()
        request.filter(matching: \.artistName, equalTo: artistName)
        request.sort(by: \.title, ascending: true)
        let response = try await request.response()

        return response.items.map { song in
            TrackInfo(
                name: song.title,
                artist: song.artistName,
                album: song.albumTitle ?? "",
                duration: song.duration ?? 0,
                position: 0,
                albumArtist: song.artistName
            )
        }
    }

    // MARK: - Tracks by Album

    func getTracksByAlbum(_ albumName: String, artist: String?) async throws -> [TrackInfo] {
        var request = MusicLibraryRequest<Song>()
        request.filter(matching: \.albumTitle, equalTo: albumName)
        if let artist, !artist.isEmpty {
            request.filter(matching: \.artistName, equalTo: artist)
        }
        request.sort(by: \.trackNumber, ascending: true)
        let response = try await request.response()

        return response.items.map { song in
            TrackInfo(
                name: song.title,
                artist: song.artistName,
                album: song.albumTitle ?? "",
                duration: song.duration ?? 0,
                position: 0,
                albumArtist: song.artistName
            )
        }
    }

    // MARK: - Full Library Export

    /// Export every library song with its album artist, track/disc numbers
    /// and MusicKit ID.
    ///
    /// MusicKit hands out a different ID for the same song depending on the
    /// route: songs from MusicLibraryRequest<Song> carry the playable library
    /// ID, while tracks reached through an album or playlist carry another
    /// that can't be looked up again. Song has no album-artist property, so
    /// album artists come from walking albums and are joined back onto the
    /// songs by (album, title, artist, disc, track).
    func exportFullLibrary() async throws -> LibraryExportResponse {
        var songRequest = MusicLibraryRequest<Song>()
        songRequest.limit = 1_000_000
        let songs = try await songRequest.response().items

        var albumRequest = MusicLibraryRequest<Album>()
        albumRequest.limit = 1_000_000
        let albums = try await albumRequest.response().items

        var albumArtistByKey: [String: String] = [:]
        for album in albums {
            guard let albumTracks = try? await album.with(.tracks).tracks else { continue }
            for track in albumTracks {
                albumArtistByKey[Self.joinKey(track, albumTitle: album.title)] = album.artistName
            }
        }

        var songIDByKey: [String: String] = [:]
        let tracks = songs.map { song -> TrackInfo in
            let key = Self.joinKey(song)
            songIDByKey[key] = song.id.rawValue
            return Self.trackInfo(song, albumArtist: albumArtistByKey[key] ?? song.artistName)
        }

        var playlistRequest = MusicLibraryRequest<Playlist>()
        playlistRequest.sort(by: \.name, ascending: true)
        let playlistResponse = try await playlistRequest.response()

        var playlists: [PlaylistExport] = []
        for playlist in playlistResponse.items {
            let detailed = try await playlist.with(.tracks)
            let playlistTracks: [TrackInfo] = (detailed.tracks ?? []).compactMap { track in
                guard case .song(let song) = track,
                      let id = songIDByKey[Self.joinKey(track)] else { return nil }
                var info = Self.trackInfo(song, albumArtist: song.artistName)
                info.id = id
                return info
            }
            playlists.append(PlaylistExport(
                id: playlist.id.rawValue, name: playlist.name, tracks: playlistTracks
            ))
        }

        return LibraryExportResponse(tracks: tracks, playlists: playlists)
    }

    private static func joinKey(_ song: Song) -> String {
        joinKey(album: song.albumTitle, title: song.title, artist: song.artistName,
                disc: song.discNumber, track: song.trackNumber)
    }

    private static func joinKey(_ track: Track, albumTitle: String? = nil) -> String {
        joinKey(album: track.albumTitle ?? albumTitle, title: track.title, artist: track.artistName,
                disc: track.discNumber, track: track.trackNumber)
    }

    private static func joinKey(album: String?, title: String, artist: String, disc: Int?, track: Int?) -> String {
        [album ?? "", title, artist, String(disc ?? 0), String(track ?? 0)]
            .map { $0.lowercased() }
            .joined(separator: "\u{1F}")
    }

    private static func trackInfo(_ song: Song, albumArtist: String) -> TrackInfo {
        return TrackInfo(
            name: song.title,
            artist: song.artistName,
            album: song.albumTitle ?? "",
            duration: song.duration ?? 0,
            position: 0,
            albumArtist: albumArtist,
            id: song.id.rawValue,
            trackNumber: song.trackNumber,
            discNumber: song.discNumber
        )
    }

    // MARK: - Search

    func searchLibrary(query: String, limit: Int = 50) async throws -> [TrackInfo] {
        let request = MusicLibrarySearchRequest(term: query, types: [Song.self])
        let response = try await request.response()

        let songs = Array(response.songs.prefix(limit))
        return songs.map { song in
            TrackInfo(
                name: song.title,
                artist: song.artistName,
                album: song.albumTitle ?? "",
                duration: song.duration ?? 0,
                position: 0,
                albumArtist: song.artistName
            )
        }
    }
}
