// Imagina Cloud (IMAGINA.md). New file in imagina/Sources: updates of Nextcloud never conflict with it.

import SwiftUI

/// The foot of Settings, where the app says what it is: the wordmark («imagina /cloud») above the notice with the
/// version, the Nextcloud server and the statement that this is a modified version of Nextcloud for iOS, not the
/// official app.
struct ImaginaAboutFooter: View {
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Image("logo")
                .resizable()
                .scaledToFit()
                .frame(height: 28)
                .accessibilityLabel(NCBrandOptions.shared.brand)

            Text(text)
                .font(.custom("InstrumentSans-Regular", size: 13, relativeTo: .footnote))
        }
    }
}
