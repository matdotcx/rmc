BINARY = .build/debug/rmcd
APP_BUNDLE = .build/rmcd.app
CONTENTS = $(APP_BUNDLE)/Contents
MACOS = $(CONTENTS)/MacOS
# Sign with the stable local identity (see `make cert`) so macOS keeps the
# daemon's Apple Music / Automation permissions across rebuilds. Ad-hoc
# signing ("-") changes identity on every build and re-prompts for them.
SIGNING_NAME = rmcd Local Code Signing
IDENTITY ?= $(if $(shell security find-certificate -c "$(SIGNING_NAME)" >/dev/null 2>&1 && echo y),$(SIGNING_NAME),-)

LABEL = org.iaconelli.rmcd
LAUNCH_AGENT = $(HOME)/Library/LaunchAgents/$(LABEL).plist
UID := $(shell id -u)

.PHONY: build bundle sign cert clean run install uninstall

build:
	swift build

bundle: build
	mkdir -p $(MACOS)
	cp $(BINARY) $(MACOS)/rmcd
	cp Info.plist $(CONTENTS)/Info.plist

sign: bundle
ifeq ($(IDENTITY),-)
	@echo "WARNING: ad-hoc signing; permissions will be re-requested after every rebuild." >&2
	@echo "         Run 'make cert' once to create a stable signing identity." >&2
endif
	codesign --force --sign "$(IDENTITY)" --entitlements rmcd.entitlements $(APP_BUNDLE) || \
		{ echo "codesign failed - if the login keychain is locked (e.g. over SSH), run:" >&2; \
		  echo "  security unlock-keychain ~/Library/Keychains/login.keychain-db" >&2; exit 1; }

# Create the stable local signing identity in the login keychain (one-off).
cert:
	../scripts/create-signing-cert.sh

run: sign
	$(APP_BUNDLE)/Contents/MacOS/rmcd --port 18895

# Install (or reinstall) the daemon as a per-user launchd agent in the GUI session.
# The agent runs scripts/start-daemon.sh, which reads ~/.config/rmc/config.json.
install: sign
	mkdir -p $(dir $(LAUNCH_AGENT)) $(HOME)/.config/rmc
	sed -e 's|@REPO@|$(abspath ..)|g' -e 's|@HOME@|$(HOME)|g' $(LABEL).plist > $(LAUNCH_AGENT)
	-launchctl bootout gui/$(UID)/$(LABEL) 2>/dev/null
	launchctl bootstrap gui/$(UID) $(LAUNCH_AGENT)

uninstall:
	-launchctl bootout gui/$(UID)/$(LABEL) 2>/dev/null
	rm -f $(LAUNCH_AGENT)
	-pkill -x rmcd

clean:
	swift package clean
	rm -rf $(APP_BUNDLE)
