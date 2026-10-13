// SPDX-FileCopyrightText: Nextcloud GmbH
// SPDX-FileCopyrightText: 2025 Marino Faggiana
// SPDX-License-Identifier: GPL-3.0-or-later

import Foundation
import SwiftUI
import RealmSwift
import NextcloudKit

/// A modal SwiftUI view responsible for maintenance database
struct Maintenance: View {
    let onCompleted: () -> Void

    var body: some View {
        ZStack {
            Color(NCBrandColor.shared.customerBackground)
                .ignoresSafeArea()
            VStack(spacing: 20) {
                Spacer()

                Image(systemName: "externaldrive.fill.badge.icloud")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 80, height: 80)
                    .foregroundColor(Color(NCBrandColor.shared.customerBackgroundText))

                Text("_opt_in_pro_")
                    .cappedFont(.body, maxDynamicType: .accessibility2)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                    .foregroundColor(Color(NCBrandColor.shared.customerBackgroundText))

                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: Color(NCBrandColor.shared.customer)))
                    .scaleEffect(1.5)
                    .padding(.top, 16)

                Spacer()
            }
            .task {
                await startMaintenance()
            }
        }
    }

    /// Executes the maintenance.
    private func startMaintenance() async {
        do {
            try NCManageDatabase.shared.compactRealm()
        } catch {
            nkLog(tag: NCGlobal.shared.logTagDatabase, emoji: .error, message: "Realm compaction failed: \(error.localizedDescription)")
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            onCompleted()
        }
    }
}
