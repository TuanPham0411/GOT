"use strict";
(function(root){
  class SessionClock {
    constructor(expiresAt, serverNow, now = Date.now) {
      this.now = now;
      this.expiresAt = Date.parse(expiresAt);
      const serverTime = Date.parse(serverNow);
      this.offset = Number.isFinite(serverTime) ? serverTime - now() : 0;
    }
    remaining() {
      if (!Number.isFinite(this.expiresAt)) return 0;
      return Math.max(0, Math.ceil((this.expiresAt - this.now() - this.offset) / 1000));
    }
  }
  if(typeof module !== "undefined" && module.exports) module.exports = SessionClock;
  else root.GOTSessionClock = SessionClock;
})(globalThis);
