import ScriptingBridge

// MARK: - Protocols (ScriptingBridge — volume only)

@objc protocol MusicApplication {
    @objc optional var soundVolume: Int { get set }
}

extension SBApplication: MusicApplication {}
