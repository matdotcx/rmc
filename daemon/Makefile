BINARY = .build/debug/rmcd
APP_BUNDLE = .build/rmcd.app
CONTENTS = $(APP_BUNDLE)/Contents
MACOS = $(CONTENTS)/MacOS
IDENTITY ?= -

LABEL = org.iaconelli.rmcd
LAUNCH_AGENT = $(HOME)/Library/LaunchAgents/$(LABEL).plist
UID := $(shell id -u)

.PHONY: build bundle sign clean run install uninstall

build:
	swift build

bundle: build
	mkdir -p $(MACOS)
	cp $(BINARY) $(MACOS)/rmcd
	cp Info.plist $(CONTENTS)/Info.plist

sign: bundle
	codesign --force --sign $(IDENTITY) --entitlements rmcd.entitlements $(APP_BUNDLE)

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
