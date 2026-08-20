=== TDCi Recovery Hub ===
Contributors: jobluemann
Tags: automotive, diagnostics, obd2, ford, showcase
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 0.1.0
License: MIT
License URI: https://opensource.org/licenses/MIT

Showcase page + anonymous community fault collector for the ford-tdci-recovery open-source Ford 2.0 TDCi diagnostic suite.

== Description ==

TDCi Recovery Hub adds a self-contained showcase page for the
[ford-tdci-recovery](https://github.com/jobluemann/ford-tdci-recovery)
project to any WordPress site:

* **Auto-creates its own page** on activation (`/ford-tdci-diagnostics`) —
  your homepage and existing content are never touched.
* **Embeds the phone app (PWA)** — visitors can run the known-issue lookup
  in their browser, offline-capable, no install.
* **Shows real app screenshots** (bundled, served locally).
* **Anonymous community fault collector** — a REST endpoint
  (`/wp-json/tdci/v1/report`) accepts opt-in, VIN-stripped diagnostic
  reports from the desktop app and stores them for admin review
  ("TDCi Reports" menu). Read-only feed at `/wp-json/tdci/v1/reports`.
  Defense in depth: any submission containing a VIN field is rejected.

Built by Jo Bluemann (jobluemann.com) with Kimi AI.

== Installation ==

1. Upload `tdci-recovery-hub.zip` via Plugins → Add New → Upload Plugin.
2. Activate. The page "Ford TDCi Diagnostics" is created automatically.
3. Optional: add the page to your menu under Appearance → Menus.

== Frequently Asked Questions ==

= Does it change my homepage or theme? =
No. It creates one new page and nothing else. Deactivating leaves the page
in place (delete it manually if unwanted); no data is ever removed.

= Is any personal data collected? =
No. Reports are anonymous by design, VIN-stripped client-side, and the
collector rejects any submission containing a VIN field.

== Changelog ==

= 0.1.0 =
* Initial release: showcase page, PWA embed, screenshots, REST collector.
