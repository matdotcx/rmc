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

    func exportFullLibrary() async throws -> LibraryExportResponse {
        // Fetch all songs
        var songRequest = MusicLibraryRequest<Song>()
        songRequest.sort(by: \.title, ascending: true)
        let songResponse = try await songRequest.response()

        let tracks = songResponse.items.map { song in
            TrackInfo(
                name: song.title,
                artist: song.artistName,
                album: song.albumTitle ?? "",
                duration: song.duration ?? 0,
                position: 0,
                albumArtist: song.artistName
            )
        }

        // Fetch all playlists with their tracks
        var playlistRequest = MusicLibraryRequest<Playlist>()
        playlistRequest.sort(by: \.name, ascending: true)
        let playlistResponse = try await playlistRequest.response()

        var playlists: [PlaylistExport] = []
        for playlist in playlistResponse.items {
            let detailed = try await playlist.with(.tracks)
            let playlistTracks: [TrackInfo]
            if let t = detailed.tracks {
                playlistTracks = t.map { track in
                    TrackInfo(
                        name: track.title,
                        artist: track.artistName,
                        album: track.albumTitle ?? "",
                        duration: track.duration ?? 0,
                        position: 0,
                        albumArtist: track.artistName
                    )
                }
            } else {
                playlistTracks = []
            }
            playlists.append(PlaylistExport(name: playlist.name, tracks: playlistTracks))
        }

        return LibraryExportResponse(tracks: tracks, playlists: playlists)
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
