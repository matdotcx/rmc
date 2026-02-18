// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "rmcd",
    platforms: [
        .macOS(.v14)
    ],
    dependencies: [
        .package(url: "https://github.com/hummingbird-project/hummingbird.git", from: "2.0.0"),
        .package(url: "https://github.com/apple/swift-argument-parser.git", from: "1.3.0"),
    ],
    targets: [
        .executableTarget(
            name: "rmcd",
            dependencies: [
                .product(name: "Hummingbird", package: "hummingbird"),
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ],
            path: "Sources/rmcd",
            linkerSettings: [
                .linkedFramework("ScriptingBridge"),
            ]
        ),
    ]
)
