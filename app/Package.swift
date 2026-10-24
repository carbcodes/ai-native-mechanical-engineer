// swift-tools-version:5.9
// Mechy macOS app (Phase 0 shell). Build: `swift build` / `swift run Mechy`, or open this file in Xcode.
import PackageDescription

let package = Package(
    name: "Mechy",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Mechy", targets: ["Mechy"])
    ],
    dependencies: [
        // YAML reading for the project contract files (contracts.md sections 1-5).
        .package(url: "https://github.com/jpsim/Yams.git", from: "5.1.0")
    ],
    targets: [
        .executableTarget(
            name: "Mechy",
            dependencies: [.product(name: "Yams", package: "Yams")],
            path: "Sources/Mechy",
            resources: [.copy("Resources/viewer")]
        ),
        .testTarget(
            name: "MechyTests",
            dependencies: ["Mechy", .product(name: "Yams", package: "Yams")],
            path: "Tests/MechyTests"
        )
    ]
)
