import Foundation
import Hummingbird

func buildRouter(
    controller: MusicController,
    library: MusicKitLibrary,
    authManager: AuthorizationManager,
    startTime: Date
) -> Router<BasicRequestContext> {
    let router = Router()
    let api = router.group("api/v1")

    // MARK: - System

    api.get("system/health") { _, _ -> Response in
        let uptime = Date().timeIntervalSince(startTime)
        let body = HealthResponse(version: "0.1.0", uptime: uptime)
        return try encodeJSON(body)
    }

    // MARK: - Combined Status

    api.get("status") { _, _ -> Response in
        do {
            let status = try await controller.getStatus()
            return try encodeJSON(status)
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    // MARK: - Playback

    api.post("playback/play") { _, _ -> Response in
        do {
            try await controller.play()
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.post("playback/pause") { _, _ -> Response in
        do {
            try await controller.pause()
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.post("playback/playpause") { _, _ -> Response in
        do {
            try await controller.playpause()
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.post("playback/next") { _, _ -> Response in
        do {
            try await controller.nextTrack()
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.post("playback/previous") { _, _ -> Response in
        do {
            try await controller.previousTrack()
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.post("playback/seek") { request, context -> Response in
        do {
            let body = try await decodeJSON(SeekRequest.self, from: request, context: context)
            try await controller.setPlayerPosition(body.position)
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .badRequest)
        }
    }

    api.post("playback/play-track") { request, context -> Response in
        do {
            let body = try await decodeJSON(PlayTrackRequest.self, from: request, context: context)
            try await controller.playTrack(name: body.name, artist: body.artist)
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.post("playback/play-playlist") { request, context -> Response in
        do {
            let body = try await decodeJSON(PlayPlaylistRequest.self, from: request, context: context)
            try await controller.playPlaylist(name: body.name)
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    // MARK: - Settings

    api.put("settings/volume") { request, context -> Response in
        do {
            let body = try await decodeJSON(VolumeRequest.self, from: request, context: context)
            try await controller.setVolume(body.level)
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .badRequest)
        }
    }

    api.put("settings/shuffle") { request, context -> Response in
        do {
            let body = try await decodeJSON(ShuffleRequest.self, from: request, context: context)
            try await controller.setShuffle(body.enabled)
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .badRequest)
        }
    }

    api.put("settings/repeat") { request, context -> Response in
        do {
            let body = try await decodeJSON(RepeatRequest.self, from: request, context: context)
            try await controller.setRepeat(body.mode)
            return try encodeJSON(OKResponse())
        } catch {
            return try errorResponse(error, status: .badRequest)
        }
    }

    // MARK: - Library (MusicKit)

    api.get("library/artists") { _, _ -> Response in
        do {
            let artists = try await library.getAllArtists()
            return try encodeJSON(ArtistsResponse(artists: artists))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.get("library/albums") { _, _ -> Response in
        do {
            let albums = try await library.getAllAlbums()
            return try encodeJSON(AlbumsResponse(albums: albums))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.get("library/playlists") { _, _ -> Response in
        do {
            let playlists = try await library.getPlaylists()
            return try encodeJSON(PlaylistsResponse(playlists: playlists))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.get("library/playlists/:name") { _, context -> Response in
        let name = context.parameters.get("name") ?? ""
        do {
            let tracks = try await library.getPlaylistTracks(name: name)
            return try encodeJSON(TracksResponse(tracks: tracks))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.get("library/artists/:name") { _, context -> Response in
        let name = context.parameters.get("name") ?? ""
        do {
            let tracks = try await library.getTracksByArtist(name)
            return try encodeJSON(TracksResponse(tracks: tracks))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.get("library/albums/:name") { request, context -> Response in
        let name = context.parameters.get("name") ?? ""
        let artist = request.uri.queryParameters.get("artist")
        do {
            let tracks = try await library.getTracksByAlbum(name, artist: artist)
            return try encodeJSON(TracksResponse(tracks: tracks))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    api.get("library/search") { request, _ -> Response in
        let query = request.uri.queryParameters.get("q") ?? ""
        let limitStr = request.uri.queryParameters.get("limit") ?? "50"
        let limit = Int(limitStr) ?? 50
        if query.isEmpty {
            return try encodeJSON(TracksResponse(tracks: []))
        }
        do {
            let tracks = try await library.searchLibrary(query: query, limit: limit)
            return try encodeJSON(TracksResponse(tracks: tracks))
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    // MARK: - Library Export (full index for Python client)

    api.post("library/index") { _, _ -> Response in
        do {
            let export = try await library.exportFullLibrary()
            return try encodeJSON(export)
        } catch {
            return try errorResponse(error, status: .internalServerError)
        }
    }

    // MARK: - Auth (MusicKit)

    api.get("system/auth") { _, _ -> Response in
        let status = await authManager.currentStatus()
        return try encodeJSON(AuthStatusResponse(status: status))
    }

    api.post("system/authorize") { _, _ -> Response in
        let status = await authManager.requestAuthorization()
        return try encodeJSON(AuthStatusResponse(status: status))
    }

    return router
}

// MARK: - Helpers

private let jsonEncoder: JSONEncoder = {
    let e = JSONEncoder()
    e.keyEncodingStrategy = .useDefaultKeys
    return e
}()

private let jsonDecoder: JSONDecoder = {
    let d = JSONDecoder()
    d.keyDecodingStrategy = .useDefaultKeys
    return d
}()

private func encodeJSON<T: Encodable>(_ value: T, status: HTTPResponse.Status = .ok) throws -> Response {
    let data = try jsonEncoder.encode(value)
    return Response(
        status: status,
        headers: [.contentType: "application/json"],
        body: .init(byteBuffer: .init(data: data))
    )
}

private func decodeJSON<T: Decodable>(
    _ type: T.Type,
    from request: Request,
    context: BasicRequestContext
) async throws -> T {
    let body = try await request.body.collect(upTo: 1_048_576)
    return try jsonDecoder.decode(type, from: body)
}

private func errorResponse(_ error: Error, status: HTTPResponse.Status) throws -> Response {
    let body = ErrorResponse(error: error.localizedDescription)
    return try encodeJSON(body, status: status)
}
