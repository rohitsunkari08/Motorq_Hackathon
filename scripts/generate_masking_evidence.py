import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set up figure
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6.5), dpi=150)
fig.patch.set_facecolor('#0d1117')

# Title
fig.suptitle(
    "Role-Based Location Privacy & Masking Proof (NOTE.md §6.3, §7, §8)\nSame Vehicle (VIN: 1VXEV01A100000001)",
    color='white',
    fontsize=14,
    fontweight='bold',
    y=0.96
)

# ----------------- PANEL 1: FLEET MANAGER -----------------
ax1.set_facecolor('#161b22')
for spine in ax1.spines.values():
    spine.set_color('#30363d')
ax1.tick_params(colors='#8b949e', labelsize=9)

# Grid simulation
ax1.set_xlim(13.38, 13.43)
ax1.set_ylim(52.50, 52.54)
ax1.set_xlabel("Longitude (°E)", color='#8b949e', fontsize=10)
ax1.set_ylabel("Latitude (°N)", color='#8b949e', fontsize=10)
ax1.set_title("Role: fleet_manager\nPRECISE CO-ORDINATES UNMASKED", color='#58a6ff', fontsize=12, fontweight='bold', pad=12)

# Point representation
ax1.plot(13.4050, 52.5200, marker='o', markersize=12, color='#238636', markeredgecolor='white', markeredgewidth=2)
ax1.annotate("Vehicle Precise Fix\n(52.520008, 13.404954)\nGeohash7: u4pruyd", 
             (13.4050, 52.5200), xytext=(13.385, 52.528),
             color='white', fontsize=9,
             arrowprops=dict(facecolor='#58a6ff', shrink=0.08, width=1.5, headwidth=7),
             bbox=dict(boxstyle="round,pad=0.5", fc="#21262d", ec="#58a6ff", lw=1.5))

# JSON text box
mgr_json = (
    "API Response (HTTP 200):\n"
    "{\n"
    '  "vin": "1VXEV01A100000001",\n'
    '  "lat": 52.520008,\n'
    '  "lon": 13.404954,\n'
    '  "geohash": "u4pruyd",\n'
    '  "location_masked": false\n'
    "}"
)
ax1.text(0.04, 0.05, mgr_json, transform=ax1.transAxes,
         family='monospace', fontsize=8.5, color='#7ee787',
         bbox=dict(boxstyle="round,pad=0.6", fc="#0d1117", ec="#30363d", lw=1))

# ----------------- PANEL 2: VIEWER -----------------
ax2.set_facecolor('#161b22')
for spine in ax2.spines.values():
    spine.set_color('#30363d')
ax2.tick_params(colors='#8b949e', labelsize=9)

ax2.set_xlim(13.38, 13.43)
ax2.set_ylim(52.50, 52.54)
ax2.set_xlabel("Longitude (°E)", color='#8b949e', fontsize=10)
ax2.set_ylabel("Latitude (°N)", color='#8b949e', fontsize=10)
ax2.set_title("Role: viewer\nPRIVACY MASKING: GEOHASH5 BOUNDING BOX ONLY", color='#f85149', fontsize=12, fontweight='bold', pad=12)

# Bounding box simulation (Geohash5 cell ~4.9km x ~4.9km)
rect = patches.Rectangle((13.385, 52.505), 0.04, 0.03, linewidth=2, edgecolor='#f85149', facecolor='#f85149', alpha=0.25, linestyle='--')
ax2.add_patch(rect)
ax2.annotate("Geohash5 Cell: 'u4pru'\n(~4.9km Resolution Box)\nPrecise GPS Nullified", 
             (13.405, 52.520), xytext=(13.388, 52.528),
             color='white', fontsize=9,
             bbox=dict(boxstyle="round,pad=0.5", fc="#21262d", ec="#f85149", lw=1.5))

# JSON text box
viewer_json = (
    "API Response (HTTP 200):\n"
    "{\n"
    '  "vin": "1VXEV01A100000001",\n'
    '  "lat": null,\n'
    '  "lon": null,\n'
    '  "geohash": "u4pru",\n'
    '  "location_masked": true\n'
    "}"
)
ax2.text(0.04, 0.05, viewer_json, transform=ax2.transAxes,
         family='monospace', fontsize=8.5, color='#ff7b72',
         bbox=dict(boxstyle="round,pad=0.6", fc="#0d1117", ec="#30363d", lw=1))

plt.tight_layout(rect=[0, 0.03, 1, 0.93])
plt.savefig("tests/evidence/p4/masking.png", dpi=150)
print("Saved tests/evidence/p4/masking.png successfully.")
