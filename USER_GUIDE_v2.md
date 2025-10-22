# CRPM v2.0 - User Guide

## Quick Start

### Running the Application

```bash
cd C:\Users\hugof\CRPM
streamlit run app_v2.py
```

The application will open in your browser at http://localhost:8502

---

## Application Overview

CRPM v2.0 provides a comprehensive process mining workbench with 5 main tabs:

1. **🔍 Discovery** - View all discovered process models
2. **📊 Model Comparison** - Compare conformance metrics across algorithms
3. **⚡ Performance Analytics** - Identify bottlenecks and analyze durations
4. **🔀 Variant Analysis** - Examine trace variants and their conformance
5. **🗺️ DFG Visualizations** - Visualize directly-follows graphs

---

## Step-by-Step Workflow

### Step 1: Load Your Data

**Sidebar → Input Source**

#### Option A: XES Files
1. Select "XES" radio button
2. Specify folder containing .xes files (default: `./xes_logs`)
3. Select a log from dropdown OR upload a new XES file
4. Sample log `running-example.xes` is included for testing

#### Option B: CSV Files
1. Select "CSV" radio button
2. Click "Upload CSV log" and choose your file
3. Map columns:
   - **Case ID column**: Unique identifier for each process instance
   - **Activity column**: Name of the activity/task
   - **Timestamp column**: When the activity occurred
4. Preview will show automatically

### Step 2: Apply Filters (Optional)

**Sidebar → Filters**

- **Filter by first event**: Select specific starting activity or "All"
- **Apply date filter**: Check box and set start/end dates
  - Only traces within this period will be analyzed
- **Log Statistics** section shows:
  - Total traces and events
  - Date range of the log

### Step 3: Select Algorithms

**Sidebar → Discovery Algorithms**

Click "Select Algorithms" expander:

**Heuristics Miner** (dependency-based):
- ☑ Heuristics (Classic) - Standard algorithm
- ☐ Heuristics (PLUS) - Enhanced variant

**Inductive Miner** (tree-based, sound models):
- ☑ Inductive (IMf) - Handles noise well (recommended)
- ☐ Inductive (IM) - Classic variant
- ☐ Inductive (IMd) - Directly-follows variant

**Alpha Miner** (academic):
- ☐ Alpha (Classic) - Basic algorithm
- ☐ Alpha+ - Enhanced variant

**Tips:**
- Select "Select All" to run all 7 algorithms
- Minimum 1 algorithm required
- More algorithms = longer processing time but better comparison

### Step 4: Run Analysis

**Sidebar → 🚀 Run Analysis Button**

1. Click the **🚀 Run Analysis** button
2. Progress indicators will show:
   - Applying filters...
   - Running process discovery algorithms...
   - Discovery complete!
3. Results are cached for fast re-access

---

## Exploring the Results

### Tab 1: 🔍 Discovery

**What You See:**
- All discovered models displayed side-by-side
- Model statistics for each:
  - Number of transitions (activities)
  - Number of places (states)
  - Number of arcs (connections)
  - Discovery time

**What You Can Do:**
- View model visualizations
- Download individual model images (PNG)
- Compare model complexity at a glance

**Interpretation:**
- **More transitions** = More activities captured
- **More places** = More complex state space
- **Faster discovery** = Simpler algorithm or smaller log

---

### Tab 2: 📊 Model Comparison & Sensitivity Analysis

**What You See:**
- Conformance metrics table for all models
- Fitness vs Precision scatter plot (Pareto frontier)
- Metrics heatmap
- Model recommendations

**Key Metrics:**

| Metric | What It Means | Good Value |
|--------|---------------|------------|
| **Alignment Fitness** | How well log replays in model | Close to 1.0 |
| **Token Fitness** | Replay fitness (alternative method) | Close to 1.0 |
| **Precision** | Model doesn't allow too much behavior | Close to 1.0 |
| **Arc Degree** | Average connections per node | Lower = simpler |
| **Complexity Score** | Overall model complexity | Lower = simpler |

**Pareto Frontier:**
- Upper-right corner = best models (high fitness + precision)
- Green zone (0.8-1.0 both axes) = acceptable models

**Recommendations:**
- **Best Fitness**: Highest replay success
- **Best Precision**: Most accurate model
- **Best Balanced**: Optimal trade-off

**What You Can Do:**
- Sort comparison table by any metric
- Download comparison as CSV
- Identify which algorithm works best for your process

---

### Tab 3: ⚡ Performance Analytics & Bottleneck Detection

**Select a Model**: Choose which discovered model to analyze

**Case Duration Statistics:**
- Total cases, median, average, P90, max duration
- Shows overall process throughput

**Top Bottlenecks Chart:**
- Horizontal bar chart showing slowest transitions
- **Orange bars**: Median duration
- **Red bars**: P90 duration (90th percentile)
- Transitions ranked by bottleneck score (duration × frequency)

**Activity Statistics Table:**
- Min/Avg/Median/Max/P90 duration for each activity
- Frequency = how many times activity occurred
- Coefficient of Variation (CV) = consistency measure
  - High CV = highly variable durations
  - Low CV = consistent durations

**Case Duration Distribution:**
- Histogram showing how long cases take
- Red dashed line = median
- Blue dotted line = mean
- Identify outliers and process variation

**What You Can Do:**
- Identify which transitions are slowest
- Download bottleneck data (CSV)
- Download activity statistics (CSV)
- Focus improvement efforts on top bottlenecks

**Interpretation:**
- **High median duration**: Structural bottleneck
- **High P90 but low median**: Occasional delays
- **High frequency + high duration**: Critical bottleneck

---

### Tab 4: 🔀 Variant Analysis

**Configuration:**
- Slider: Number of top variants to analyze (5-50)
- Select model for variant conformance

**Variant Frequency Distribution:**
- Bar chart showing most common trace variants
- Y-axis = percentage of total traces
- X-axis = variant rank (1 = most frequent)

**Cumulative Variant Coverage:**
- Shows how many variants account for X% of traces
- Metrics shown:
  - Variants for 50% coverage
  - Variants for 80% coverage (Pareto principle)
  - Variants for 90% coverage

**Per-Variant Conformance Table:**
- Each row = one variant (activity sequence)
- Columns:
  - **Frequency**: How many times this variant occurred
  - **Percentage**: % of total traces
  - **Token Fitness**: Conformance score
  - **Alignment Fitness**: Conformance score (alternative)
  - **Perfect Fit %**: % of traces with perfect conformance

**Non-Conforming Variants:**
- Expandable section shows variants with fitness < 0.8
- These variants don't fit the model well
- Investigate for process deviations or model issues

**What You Can Do:**
- Identify most common process paths
- Find conformance issues by variant
- Download variant conformance (CSV)
- Focus on variants covering 80% of cases (Pareto)

**Interpretation:**
- **High frequency + low fitness**: Common deviation pattern
- **Low frequency + low fitness**: Rare exceptional cases
- **Long variant string**: Complex process path

---

### Tab 5: 🗺️ DFG Visualizations

**DFG Type Selection:**
- **Frequency-Based**: Shows how often transitions occur
  - Edge thickness = frequency
  - Numbers on edges = count
- **Performance-Based**: Shows how long transitions take
  - Edge labels = median duration
  - Numbers show seconds (and hours in tooltip)

**Filtering Options:**
- **Minimum edge frequency**: Hide rare transitions
- **Keep top % of edges**: Show only busiest paths (e.g., top 80%)
- Filtered statistics show how many activities/edges remain

**DFG Visualization:**
- Nodes = activities
- Edges = direct transitions between activities
- Start activities = green nodes
- End activities = red nodes

**DFG Edge Details:**
- Expandable table shows all edges
- Sortable by frequency or duration
- Download as CSV

**What You Can Do:**
- Understand process flow at a glance
- Identify most common paths (frequency mode)
- Identify slow transitions (performance mode)
- Filter out noise (rare transitions)
- Download DFG image (PNG)
- Download edge data (CSV)

**Interpretation:**
- **Thick edges**: Frequent transitions
- **Many incoming edges**: Convergence point
- **Many outgoing edges**: Decision point
- **High duration**: Performance bottleneck

---

## Export Options

Throughout the application, you can export:

| What | Format | Where |
|------|--------|-------|
| Model visualizations | PNG | Tab 1: Discovery |
| Comparison table | CSV | Tab 2: Model Comparison |
| Bottleneck data | CSV | Tab 3: Performance Analytics |
| Activity statistics | CSV | Tab 3: Performance Analytics |
| Variant conformance | CSV | Tab 4: Variant Analysis |
| DFG visualization | PNG | Tab 5: DFG Visualizations |
| DFG edge data | CSV | Tab 5: DFG Visualizations |

---

## Tips & Best Practices

### For Small Logs (<1,000 traces)
- ✅ Run all algorithms
- ✅ Analyze all variants
- ✅ Use Alpha Miner for academic insights

### For Medium Logs (1,000-50,000 traces)
- ✅ Run Heuristics + Inductive algorithms
- ✅ Analyze top 20-30 variants
- ⚠ Alignments may be slow, be patient

### For Large Logs (>50,000 traces)
- ✅ Use filters to reduce log size first
- ✅ Select Inductive (IMf) for best performance
- ✅ Analyze top 10-15 variants only
- ⚠ Avoid Alpha Miner (very slow)

### Algorithm Selection Guide

**When to use Heuristics Miner:**
- Process has loops and complex dependencies
- Want to see frequency-weighted edges
- Need fast discovery

**When to use Inductive Miner:**
- Want sound models (no deadlocks)
- Process has noise/incomplete traces (use IMf)
- Need hierarchical structure

**When to use Alpha Miner:**
- Academic/research purposes
- Small, clean logs
- Want to understand algorithm limitations

---

## Troubleshooting

### "No traces remain after applying filters"
- **Solution**: Relax date filters or remove first event filter

### "Graphviz executables not found" (DFG error)
- **Solution**: Install Graphviz system package
  ```bash
  # Windows (using Chocolatey)
  choco install graphviz

  # Or download from: https://graphviz.org/download/
  ```

### Discovery is very slow
- **Solution**:
  - Apply filters to reduce log size
  - Select fewer algorithms
  - Use Inductive (IMf) instead of Alpha

### Out of memory
- **Solution**:
  - Filter log by date range
  - Reduce number of variants analyzed
  - Close and restart app to clear cache

### Conformance metrics show "N/A"
- **Cause**: Model or log structure incompatible
- **Solution**: Try different algorithm or check log quality

---

## Keyboard Shortcuts

- **R**: Rerun analysis (Streamlit default)
- **Ctrl+R**: Refresh page
- **Ctrl+Click** on links: Open in new tab

---

## Advanced Features

### Caching Behavior
- All computations are automatically cached
- Re-running with same parameters is instant
- Toast notification shows "Loaded cached results"
- To clear cache: Refresh page (Ctrl+R)

### Algorithm Variants Explained

**Heuristics PLUS vs Classic:**
- PLUS handles long-distance dependencies better
- Classic is faster

**Inductive IMf vs IM vs IMd:**
- **IMf**: Filters infrequent behavior (best for noisy logs)
- **IM**: Classic, strict conformance
- **IMd**: Uses directly-follows graph (fastest)

**Alpha+ vs Classic:**
- Alpha+ handles some loop patterns
- Both struggle with complex constructs

---

## Sample Workflow: Finding and Fixing Bottlenecks

1. **Load your log** (Tab: Sidebar)
2. **Run all algorithms** → Click 🚀 Run Analysis
3. **Compare models** (Tab 2) → Choose best balanced model
4. **Identify bottlenecks** (Tab 3) → Note top 3 bottlenecks
5. **Check variants** (Tab 4) → See if bottlenecks affect all variants
6. **Visualize flow** (Tab 5) → Understand process context
7. **Export data** → Share findings with stakeholders

---

## Support & Resources

- **PM4Py Documentation**: https://pm4py.fit.fraunhofer.de/
- **Streamlit Documentation**: https://docs.streamlit.io/
- **GitHub Issues**: Report bugs in your repository
- **Sample Log**: `xes_logs/running-example.xes` included

---

## Glossary

| Term | Definition |
|------|------------|
| **Activity** | Single step/task in a process |
| **Case/Trace** | Complete process instance (start to end) |
| **Variant** | Unique sequence of activities |
| **Fitness** | How well log replays in discovered model (0-1) |
| **Precision** | How much extra behavior model allows (0-1) |
| **Alignment** | Optimal matching between log trace and model |
| **Token Replay** | Simulating token flow through Petri net |
| **Petri Net** | Formal model with places, transitions, arcs |
| **DFG** | Directly-Follows Graph (activity → next activity) |
| **Bottleneck** | Transition with long duration or high frequency |

---

*CRPM v2.0 User Guide - Last Updated: 2025-10-20*
