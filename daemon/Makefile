BINARY = .build/debug/rmcd
APP_BUNDLE = .build/rmcd.app
CONTENTS = $(APP_BUNDLE)/Contents
MACOS = $(CONTENTS)/MacOS
IDENTITY ?= -

.PHONY: build bundle sign clean run

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

clean:
	swift package clean
	rm -rf $(APP_BUNDLE)
