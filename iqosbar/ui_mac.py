"""macOS menu bar front-end.

A status item with the battery % next to the icon; clicking it opens a
popover that renders the panel (panel.py) in a WKWebView. Device reads run on
a worker thread so the menu bar never stalls.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import objc
from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSImageLeft,
    NSMakeRect,
    NSMinYEdge,
    NSPopover,
    NSPopoverBehaviorTransient,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSViewController,
)
from Foundation import NSObject, NSTimer
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration

from . import chart, panel
from .core import Poller

REFRESH_SECONDS = 20
PANEL_WIDTH = 316
# In a PyInstaller bundle the assets live under sys._MEIPASS.
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ICON_PATH = _BASE / "assets" / "menubar@2x.png"

WKScriptMessageHandler = objc.protocolNamed("WKScriptMessageHandler")


class AppDelegate(NSObject, protocols=[WKScriptMessageHandler]):
    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.poller = Poller()
        self.state = None
        self.busy = False
        return self

    # --- setup -------------------------------------------------------------

    def applicationDidFinishLaunching_(self, _note):
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        button = self.item.button()
        if ICON_PATH.exists():
            image = NSImage.alloc().initWithContentsOfFile_(str(ICON_PATH))
            image.setSize_((22, 16))
            image.setTemplate_(True)
            button.setImage_(image)
            button.setImagePosition_(NSImageLeft)
        else:
            button.setTitle_("IQOS")
        button.setTarget_(self)
        button.setAction_("togglePopover:")

        config = WKWebViewConfiguration.alloc().init()
        config.userContentController().addScriptMessageHandler_name_(self, "iqos")
        self.webview = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, PANEL_WIDTH, 300), config
        )
        self.webview.setValue_forKey_(False, "drawsBackground")

        controller = NSViewController.alloc().init()
        controller.setView_(self.webview)
        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(NSPopoverBehaviorTransient)
        self.popover.setAnimates_(True)
        self.popover.setContentViewController_(controller)
        self.popover.setContentSize_((PANEL_WIDTH, 300))

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            REFRESH_SECONDS, self, "tick:", None, True
        )
        self.refresh()

    # --- polling -----------------------------------------------------------

    def tick_(self, _timer):
        self.refresh()

    @objc.python_method
    def refresh(self):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._work, daemon=True).start()

    @objc.python_method
    def _work(self):
        try:
            state = self.poller.poll()
        except Exception:
            state = None
        AppHelper.callAfter(self._apply, state)

    @objc.python_method
    def _apply(self, state):
        self.busy = False
        if state is None:
            return
        self.state = state
        self.item.button().setTitle_(f" {state.badge}" if state.badge else "")
        self._render()

    @objc.python_method
    def _render(self):
        if self.state is not None:
            self.webview.loadHTMLString_baseURL_(panel.render(self.state), None)

    # --- popover -----------------------------------------------------------

    def togglePopover_(self, sender):
        if self.popover.isShown():
            self.popover.performClose_(sender)
            return
        self._render()
        button = self.item.button()
        NSApp.activateIgnoringOtherApps_(True)
        self.popover.showRelativeToRect_ofView_preferredEdge_(
            button.bounds(), button, NSMinYEdge
        )
        self.refresh()

    # --- messages from the panel ------------------------------------------

    def userContentController_didReceiveScriptMessage_(self, _controller, message):
        body = str(message.body())
        if body.startswith("h:"):
            try:
                height = int(body[2:]) + 2
            except ValueError:
                return
            self.popover.setContentSize_((PANEL_WIDTH, height))
        elif body == "chart":
            self.popover.performClose_(None)
            chart.open_chart()
        elif body == "refresh":
            self.refresh()
        elif body == "quit":
            NSApp.terminate_(None)


def main() -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
