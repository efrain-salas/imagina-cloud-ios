// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import UIKit

/// «Configurar el correo de este iPhone»: the iPhone's own Mail app gets the person's Imagina mailboxes from a
/// configuration profile, which iOS only installs from Safari. The app explains the steps that follow in Settings,
/// asks Imagina's devices API for a one-time link to the profile of this device (docs/PLAN_CLOUD.md, C7.2) and opens
/// it in Safari.
///
/// The row is in the Menu tab while this iPhone is a connected device. It also comes up once, right after
/// «Entrar con Imagina».
@MainActor
enum ImaginaMailSetup {
    typealias Reload = @MainActor () -> Void

    struct MenuItem {
        let title: String
        let image: String
        let action: @MainActor () -> Void
    }

    private static var lastStateCheck = Date.distantPast
    private static var isCheckingState = false

    // MARK: - Menu

    /// The row of the Menu tab, or nil when this iPhone is not a connected device. Its label comes from the last
    /// state of the profile the app knows; the state is asked from Imagina in the background and, when it differs,
    /// `reload` builds the Menu again.
    static func menuItem(presentingFrom controller: UIViewController?, reload: @escaping Reload) -> MenuItem? {
        guard ImaginaSignIn.isEnabled, let session = ImaginaStore.load(), session.deviceId != nil else {
            return nil
        }
        refreshState(reload: reload)

        let title = session.mailProfile == .changed ? ImaginaText.mailUpdateMenu : ImaginaText.mailSetupMenu
        return MenuItem(title: title, image: "envelope") { [weak controller] in
            explain(from: controller, cancelTitle: ImaginaText.cancel, reload: reload)
        }
    }

    /// Asks Imagina whether the device is still connected and what state its mail profile is in.
    private static func refreshState(reload: @escaping Reload) {
        guard !isCheckingState,
              Date().timeIntervalSince(lastStateCheck) > 60,
              let deviceId = ImaginaStore.load()?.deviceId else {
            return
        }
        isCheckingState = true

        Task {
            defer {
                isCheckingState = false
                lastStateCheck = Date()
            }
            do {
                let state = try await ImaginaApi.shared.status(of: deviceId)
                guard ImaginaStore.load()?.deviceId == deviceId else { return }

                if state.revoked {
                    ImaginaDevice.forgetRevoked()
                    reload()
                } else if ImaginaStore.load()?.mailProfile != state.mailProfile {
                    ImaginaStore.update { $0.mailProfile = state.mailProfile }
                    reload()
                }
            } catch ImaginaFailure.revoked {
                guard ImaginaStore.load()?.deviceId == deviceId else { return }
                ImaginaDevice.forgetRevoked()
                reload()
            } catch {
                // No connection, or the tokens need a new sign-in: the row keeps its label.
            }
        }
    }

    // MARK: - After «Entrar con Imagina»

    /// Offers the profile once the account exists and the app has put its main screen up.
    static func offerAfterSignIn() async {
        guard !NCManageDatabase.shared.getAllTableAccount().isEmpty, ImaginaStore.load()?.deviceId != nil else {
            return
        }
        try? await Task.sleep(nanoseconds: 1_500_000_000)

        guard let presenter = topPresenter(), !(presenter is UIAlertController) else { return }
        explain(from: presenter, cancelTitle: ImaginaText.notNow, reload: nil)
    }

    private static func topPresenter() -> UIViewController? {
        var top = UIApplication.shared.mainAppWindow?.rootViewController
        while let presented = top?.presentedViewController {
            top = presented
        }
        return top
    }

    // MARK: - Steps and link

    private static func explain(from presenter: UIViewController?, cancelTitle: String, reload: Reload?) {
        let alert = UIAlertController(title: ImaginaText.mailSetup, message: ImaginaText.mailSetupSteps, preferredStyle: .alert)
        alert.view.tintColor = ImaginaColor.accent
        alert.addAction(UIAlertAction(title: cancelTitle, style: .cancel))
        let download = UIAlertAction(title: ImaginaText.mailSetupDownload, style: .default) { _ in
            Task { await openProfile(from: presenter, reload: reload) }
        }
        alert.addAction(download)
        alert.preferredAction = download
        presenter?.present(alert, animated: true)
    }

    private static func openProfile(from presenter: UIViewController?, reload: Reload?) async {
        do {
            guard let link = try await profileLink(from: presenter) else { return }
            lastStateCheck = .distantPast
            _ = await UIApplication.shared.open(link)
        } catch {
            showFailure(error as? ImaginaFailure ?? .unexpected, from: presenter, reload: reload)
        }
    }

    /// A fresh one-time link. When the tokens are not good any more (the refresh token lasts a week), the person
    /// signs in with Imagina again only to get a token: no device is created, the one already connected is kept.
    /// Nil when the person closed that sign-in.
    private static func profileLink(from presenter: UIViewController?) async throws -> URL? {
        guard let deviceId = ImaginaStore.load()?.deviceId else { throw ImaginaFailure.revoked }

        do {
            return try await withBusy(on: presenter) { try await ImaginaApi.shared.mailProfileLink(for: deviceId) }
        } catch ImaginaFailure.needsSignIn {
            guard try await ImaginaAuthorization.signIn(from: presenter?.view.window) == .signedIn else { return nil }
            return try await withBusy(on: presenter) { try await ImaginaApi.shared.mailProfileLink(for: deviceId) }
        }
    }

    private static func showFailure(_ failure: ImaginaFailure, from presenter: UIViewController?, reload: Reload?) {
        let alert = UIAlertController(title: ImaginaText.mailSetupFailedTitle, message: failure.message, preferredStyle: .alert)
        alert.view.tintColor = ImaginaColor.accent

        if case .revoked = failure {
            // Imagina disconnected this iPhone: nothing to retry, and the Menu stops offering the profile.
            ImaginaDevice.forgetRevoked()
            reload?()
            alert.addAction(UIAlertAction(title: ImaginaText.ok, style: .default))
        } else {
            alert.addAction(UIAlertAction(title: ImaginaText.cancel, style: .cancel))
            let retry = UIAlertAction(title: ImaginaText.retry, style: .default) { _ in
                Task { await openProfile(from: presenter, reload: reload) }
            }
            alert.addAction(retry)
            alert.preferredAction = retry
        }
        presenter?.present(alert, animated: true)
    }

    // MARK: - Waiting

    /// A small «Preparando el enlace…» alert with a spinner while `work` runs.
    private static func withBusy<T>(on presenter: UIViewController?, _ work: () async throws -> T) async throws -> T {
        let busy = UIAlertController(title: ImaginaText.mailSetupPreparing, message: "\n", preferredStyle: .alert)
        let spinner = UIActivityIndicatorView(style: .medium)
        spinner.translatesAutoresizingMaskIntoConstraints = false
        spinner.startAnimating()
        busy.view.addSubview(spinner)
        NSLayoutConstraint.activate([
            spinner.centerXAnchor.constraint(equalTo: busy.view.centerXAnchor),
            spinner.bottomAnchor.constraint(equalTo: busy.view.bottomAnchor, constant: -20)
        ])
        // Dismissing while it is still coming up would be ignored by UIKit: wait until it is on screen.
        await withCheckedContinuation { continuation in
            if let presenter {
                presenter.present(busy, animated: true) { continuation.resume() }
            } else {
                continuation.resume()
            }
        }

        do {
            let result = try await work()
            await dismiss(busy)
            return result
        } catch {
            await dismiss(busy)
            throw error
        }
    }

    private static func dismiss(_ controller: UIViewController) async {
        await withCheckedContinuation { continuation in
            if controller.presentingViewController != nil {
                controller.dismiss(animated: true) { continuation.resume() }
            } else {
                continuation.resume()
            }
        }
    }
}
