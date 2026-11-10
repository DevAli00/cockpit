cask "cockpit" do
  version "0.1.0"
  sha256 "870f0e86435c7e47dc731e4cfe74b8b60a6d8b64423184552a003bb084f141d1"

  url "https://github.com/DevAli00/cockpit/releases/download/v#{version}/Cockpit-#{version}-mac-arm64.dmg"
  name "Cockpit"
  desc "Personal cockpit for tasks, goals, learning, trips and money"
  homepage "https://github.com/DevAli00/cockpit"

  depends_on arch: :arm64
  depends_on macos: :big_sur

  app "Cockpit.app"

  # Cockpit is not signed with an Apple Developer ID, so macOS would refuse to open a quarantined
  # copy. Homebrew has verified the download against the sha256 above; this clears the flag.
  postflight_steps do
    run "/usr/bin/xattr", args: ["-dr", "com.apple.quarantine", "{{appdir}}/Cockpit.app"]
  end

  caveats "Your data is kept in ~/Library/Application Support/Cockpit. Uninstalling does not delete it."
end
