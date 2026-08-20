<?php
/**
 * Plugin Name: TDCi Recovery Hub
 * Plugin URI:  https://github.com/jobluemann/ford-tdci-recovery
 * Description: Showcase page + anonymous community fault collector for the
 *              ford-tdci-recovery open-source diagnostic suite. Creates its
 *              own page on activation — never touches your homepage.
 * Version:     0.1.0
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author:      Jo Bluemann — jobluemann.com (built with Kimi AI)
 * License:     MIT
 */

if (!defined('ABSPATH')) exit;

define('TDCI_HUB_VERSION', '0.1.0');
define('TDCI_HUB_PAGE_SLUG', 'ford-tdci-diagnostics');

/* ------------------------------------------------------------------ *
 * Activation: create the showcase page (idempotent, homepage untouched)
 * ------------------------------------------------------------------ */
function tdci_hub_activate() {
    if (!get_page_by_path(TDCI_HUB_PAGE_SLUG)) {
        $id = wp_insert_post(array(
            'post_title'   => 'Ford TDCi Diagnostics',
            'post_name'    => TDCI_HUB_PAGE_SLUG,
            'post_content' => '[tdci_hub]',
            'post_status'  => 'publish',
            'post_type'    => 'page',
        ));
        if ($id && !is_wp_error($id)) {
            update_option('tdci_hub_page_id', $id);
        }
    }
}
register_activation_hook(__FILE__, 'tdci_hub_activate');

/* ------------------------------------------------------------------ *
 * Reports custom post type (admin list; no public permalinks)
 * ------------------------------------------------------------------ */
add_action('init', function () {
    register_post_type('tdci_report', array(
        'label'        => 'TDCi Reports',
        'public'       => false,
        'show_ui'      => true,
        'show_in_menu' => true,
        'menu_icon'    => 'dashicons-car',
        'supports'     => array('title'),
    ));
});

/* ------------------------------------------------------------------ *
 * [tdci_hub] showcase shortcode
 * ------------------------------------------------------------------ */
add_shortcode('tdci_hub', function () {
    $assets = plugins_url('assets', __FILE__);
    $pwa    = esc_url($assets . '/pwa/index.html');
    $gh     = 'https://github.com/jobluemann/ford-tdci-recovery';
    ob_start();
    ?>
<div class="tdci-hub" style="max-width:880px;margin:0 auto">
  <h2>Ford 2.0 TDCi diagnostics that show what your dashboard hides</h2>
  <p>Born from a real Kuga that went limp after a battery swap. Backup-first
     diagnostics, a full module scan that reveals the fault codes the
     instrument cluster never shows, a curated known-issues database with
     sources, and a free two-model AI assistant that answers grounded in
     evidence — never guessing. MIT-licensed open source.</p>
  <p>
    <a href="<?php echo esc_url($gh); ?>" target="_blank" rel="noopener">GitHub: jobluemann/ford-tdci-recovery</a>
    &nbsp;·&nbsp;
    <a href="<?php echo $pwa; ?>" target="_blank" rel="noopener">Open the phone app (PWA, works offline)</a>
  </p>

  <h3>The desktop app</h3>
  <p>
    <img src="<?php echo esc_url($assets . '/screenshots/01_main_connected.png'); ?>" alt="Main window" style="width:100%;max-width:880px;border:1px solid #dde4ea;border-radius:8px">
    <img src="<?php echo esc_url($assets . '/screenshots/02_fault_codes_module_scan.png'); ?>" alt="Fault codes and module scan" style="width:100%;max-width:880px;border:1px solid #dde4ea;border-radius:8px;margin-top:8px">
    <img src="<?php echo esc_url($assets . '/screenshots/03_ai_diagnosis.png'); ?>" alt="AI diagnosis grounded in the known-issues KB" style="width:100%;max-width:880px;border:1px solid #dde4ea;border-radius:8px;margin-top:8px">
  </p>

  <h3>Try the known-issue lookup right now</h3>
  <p>The same engine the desktop app uses, running in your browser. Type a
     symptom (e.g. <em>"scratch between gears 1 2 3"</em>) or a fault code
     (e.g. <em>P2453</em>):</p>
  <iframe src="<?php echo $pwa; ?>" title="TDCi Recovery phone app"
          style="width:100%;height:660px;border:1px solid #dde4ea;border-radius:10px"
          loading="lazy"></iframe>

  <h3>Community fault database</h3>
  <p>The desktop app can anonymously share a VIN-stripped fault report
     (opt-in only) to this site. Collected reports:
     <code><?php echo esc_html((string) wp_count_posts('tdci_report')->publish); ?></code>.
     Read-only JSON feed:
     <code><?php echo esc_url(rest_url('tdci/v1/reports')); ?></code></p>
</div>
    <?php
    return ob_get_clean();
});

/* ------------------------------------------------------------------ *
 * Anonymous community collector (ported from site/collect.php)
 *   POST /wp-json/tdci/v1/report   — store one anonymized report
 *   GET  /wp-json/tdci/v1/reports  — read-only JSON feed
 * Defense in depth: any report containing a 'vin' field is rejected.
 * ------------------------------------------------------------------ */
add_action('rest_api_init', function () {

    register_rest_route('tdci/v1', '/report', array(
        'methods'             => 'POST',
        'permission_callback' => '__return_true',
        'callback'            => function (WP_REST_Request $req) {
            $report = $req->get_json_params();
            if (!is_array($report) || ($report['schema'] ?? '') !== 'ftr-report/1') {
                return new WP_Error('bad_schema', 'invalid report schema', array('status' => 400));
            }
            if (array_key_exists('vin', $report) || strlen(wp_json_encode($report)) > 16384) {
                return new WP_Error('vin_rejected', 'reports must not contain VINs', array('status' => 400));
            }
            $report['received_utc'] = gmdate('c');
            $id = wp_insert_post(array(
                'post_type'    => 'tdci_report',
                'post_status'  => 'publish',
                'post_title'   => sanitize_text_field($report['vehicle'] ?? 'unknown') . ' — ' . gmdate('Y-m-d H:i'),
                'post_content' => wp_json_encode($report),
            ));
            if (is_wp_error($id)) {
                return new WP_Error('store_failed', 'could not store report', array('status' => 500));
            }
            return new WP_REST_Response(array('ok' => true), 201);
        },
    ));

    register_rest_route('tdci/v1', '/reports', array(
        'methods'             => 'GET',
        'permission_callback' => '__return_true',
        'callback'            => function () {
            $posts = get_posts(array(
                'post_type'   => 'tdci_report',
                'numberposts' => 200,
                'post_status' => 'publish',
            ));
            $reports = array();
            foreach ($posts as $p) {
                $r = json_decode($p->post_content, true);
                if (is_array($r)) {
                    $reports[] = $r;
                }
            }
            return array('count' => count($reports), 'reports' => $reports);
        },
    ));
});
