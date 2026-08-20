<?php
/**
 * ford-tdci-recovery community report collector.
 * Plain PHP, no frameworks, no Node. Drop on any shared host.
 *
 * POST /collect.php        -> accepts one anonymized report JSON, appends to data/reports.jsonl
 * GET  /collect.php?list=1 -> returns the collected reports as JSON (read-only)
 *
 * Reports are anonymous by design (schema ftr-report/1, VIN already stripped
 * client-side). Rejects anything containing a field named 'vin' as defense
 * in depth.
 */
header('Content-Type: application/json');
$dataDir = __DIR__ . '/data';
$file = $dataDir . '/reports.jsonl';

if (!is_dir($dataDir)) { mkdir($dataDir, 0750, true); }

if ($_SERVER['REQUEST_METHOD'] === 'GET' && isset($_GET['list'])) {
    $reports = [];
    if (file_exists($file)) {
        foreach (file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
            $r = json_decode($line, true);
            if ($r) { $reports[] = $r; }
        }
    }
    echo json_encode(['count' => count($reports), 'reports' => $reports]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'POST a JSON report, or GET ?list=1']);
    exit;
}

$raw = file_get_contents('php://input');
$report = json_decode($raw, true);
if (!is_array($report) || ($report['schema'] ?? '') !== 'ftr-report/1') {
    http_response_code(400);
    echo json_encode(['error' => 'invalid report schema']);
    exit;
}
if (array_key_exists('vin', $report) || strlen($raw) > 16384) {
    http_response_code(400);
    echo json_encode(['error' => 'reports must not contain VINs']);
    exit;
}
$report['received_utc'] = gmdate('c');
file_put_contents($file, json_encode($report) . "\n", FILE_APPEND | LOCK_EX);
http_response_code(201);
echo json_encode(['ok' => true]);
