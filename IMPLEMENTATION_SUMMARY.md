# CRPM v2.0 - Comprehensive Process Mining Workbench

## Implementation Summary

### Overview

Successfully transformed the CRPM application from a single-page process mining tool into a comprehensive multi-algorithm workbench with advanced analytics capabilities. The new version (app_v2.py) is now running on port 8502.

---

## New Features

### 1. Multi-Algorithm Discovery

**Implemented Algorithms:**
- **Heuristics Miner**: Classic and PLUS variants
- **Inductive Miner**: IM, IMf (noise-tolerant), IMd (directly-follows) variants
- **Alpha Miner**: Classic and Alpha+ variants

**Key Capabilities:**
- Run 1, 2, or all algorithms simultaneously
- Automatic caching for fast re-analysis
- Side-by-side model visualization
- Model statistics (transitions, places, arcs, discovery time)
- Download individual model visualizations

### 2. Model Comparison & Sensitivity Analysis (Tab 2)

**Conformance Metrics Computed:**
- Alignment-based fitness
- Token replay fitness
- Precision (ETConformance)
- Perfect fit percentage
- Model complexity metrics (arc degree, decision points)

**Visualizations:**
- **Fitness vs Precision Scatter Plot** - Pareto frontier analysis
- **Metrics Heatmap** - Color-coded comparison matrix
- **Comparison Table** - Sortable, downloadable CSV
- **Recommendation Engine** - Auto-suggests best model by fitness, precision, or balanced score

### 3. Performance Analytics & Bottleneck Detection (Tab 3)

**Activity-Level Statistics:**
- Frequency, min/avg/median/max/P90 duration
- Standard deviation and coefficient of variation
- Conversion to hours for readability

**Bottleneck Detection:**
- Transition-level analysis (activity → next_activity)
- Median and P90 duration metrics
- Bottleneck scoring (weighted: 70% duration, 30% frequency)
- Interactive Plotly charts with top 10 bottlenecks
- Filter by minimum occurrences (default: 3) to avoid rare transitions

**Case Duration Analysis:**
- Overall statistics (min/avg/median/P90/max)
- Case duration histogram with median/mean lines
- Quartile analysis

### 4. Variant Analysis (Tab 4)

**Variant Statistics:**
- Top-N most frequent variants (configurable 5-50)
- Frequency and percentage distribution
- Cumulative coverage analysis
- Visual frequency charts

**Per-Variant Conformance:**
- Token fitness per variant
- Alignment fitness per variant
- Perfect fit identification
- Non-conforming variant highlighting (fitness < 0.8)
- Sampled alignments for large logs (max 100 traces per variant)

**Coverage Metrics:**
- Variants needed for 50%/80%/90% coverage
- Cumulative coverage curve visualization
- Long-tail analysis

### 5. DFG Visualizations (Tab 5)

**Frequency-Based DFG:**
- Node sizes represent activity frequency
- Edge thickness represents transition frequency
- Interactive filtering by frequency threshold
- Top % edge filtering

**Performance-Based DFG:**
- Edge labels show median transition times
- Color-coded duration gradients
- Duration displayed in seconds and hours

**DFG Features:**
- Start/end activity identification
- DFG statistics (activities, edges, total value)
- Interactive sliders for filtering
- Download DFG images (PNG)
- Export edge data as CSV

---

## New Modules Created

### 1. `crpm/discovery.py`
- Multi-algorithm discovery wrappers
- `DiscoveryResult` dataclass for standardized results
- Model complexity computation
- 7 discovery functions (Heuristics Classic/PLUS, Inductive IM/IMf/IMd, Alpha Classic/Plus)

### 2. `crpm/analytics.py`
- Activity statistics computation
- Transition statistics and bottleneck detection
- Case duration analysis
- Model transition extraction from Petri nets
- Bottleneck scoring algorithm

### 3. `crpm/variants.py`
- Variant frequency statistics
- Per-variant conformance computation
- Variant coverage analysis
- Variant filtering by frequency/conformance
- Manual log filtering (replaces deprecated PM4Py sampling API)

### 4. `crpm/visualization.py`
- Plotly chart creation functions
- Bottleneck charts (horizontal bars)
- Activity duration visualizations
- Case duration histograms
- Variant frequency/coverage charts
- Model comparison charts (radar, heatmap, scatter)

### 5. `crpm/dfg_utils.py`
- DFG discovery (frequency and performance modes)
- DFG filtering by frequency/percentage
- DFG rendering to PNG
- DFG statistics computation

---

## Technical Improvements

### Architecture
- **Tab-based layout** with 5 comprehensive tabs
- **Persistent sidebar** for data loading and filtering
- **Modular design** - each tab is self-contained
- **Comprehensive caching** - 8 separate cache dictionaries for optimal performance

### Caching Strategy
```python
st.session_state = {
    "log_cache": {},              # Loaded event logs
    "dataframe_cache": {},        # CSV dataframes
    "filtered_cache": {},         # Filtered logs
    "model_cache": {},            # Legacy single-model cache
    "discovery_results_cache": {},# Multi-algorithm results
    "conformance_cache": {},      # Conformance metrics
    "performance_cache": {},      # Performance analytics
    "variant_cache": {},          # Variant analysis
    "dfg_cache": {},             # DFG graphs
}
```

### Bug Fixes
- Fixed missing `Optional` import in `crpm/conformance.py`
- Replaced deprecated `pm4py.objects.log.util.sampling.filter_log_by_variants` with manual filtering
- Updated to PM4Py 2.7.16 API compatibility

---

## User Workflow

1. **Data Input** (Sidebar)
   - Choose XES or CSV input
   - Upload files or select from folder
   - Configure filters (first event, date range)

2. **Algorithm Selection** (Sidebar)
   - Select 1, 2, or all algorithms
   - Grouped by type (Heuristics/Inductive/Alpha)
   - "Select All" option available

3. **Run Analysis** (Sidebar)
   - Single button triggers all selected algorithms
   - Progress indicators for each step
   - Background processing with caching

4. **Explore Results** (Tabs)
   - **Tab 1**: View all discovered models side-by-side
   - **Tab 2**: Compare models, identify best performers
   - **Tab 3**: Analyze performance bottlenecks
   - **Tab 4**: Deep-dive into variant behavior
   - **Tab 5**: Visualize process flow with DFGs

5. **Export Results**
   - Download model images (PNG)
   - Export comparison tables (CSV)
   - Export bottleneck data (CSV)
   - Export variant conformance (CSV)
   - Export DFG data (CSV)

---

## Performance Optimizations

### Caching
- All expensive computations are cached
- Cache keys include algorithm name and filter parameters
- Automatic cache hit detection with user feedback

### Sampling
- Variant conformance samples alignments (max 100 traces per variant)
- Reduces computation time for logs with many variants
- Configurable sampling thresholds

### Background Processing
- Discovery runs all algorithms in sequence with progress bars
- Heavy conformance computations show spinners
- User can navigate tabs while computations complete

---

## Comparison: v1 vs v2

| Feature | v1 (app.py) | v2 (app_v2.py) |
|---------|-------------|----------------|
| **Algorithms** | Heuristics, Inductive, Upload PNML | 7 algorithms across 3 families |
| **Layout** | Single page, 2 columns | 5-tab comprehensive workbench |
| **Model Comparison** | Manual | Automatic with visualizations |
| **Bottleneck Detection** | None | Full analysis with charts |
| **Variant Analysis** | None | Top-N with conformance metrics |
| **DFG** | None | Frequency & Performance modes |
| **Performance Analytics** | None | Activity stats, transition times |
| **Caching** | 5 caches | 9 caches (more granular) |
| **Export Options** | Image only | Images + CSV data for all analytics |
| **Lines of Code** | 607 | 1,103 (modular architecture) |

---

## Files Modified/Created

### Created
- ✅ `app_v2.py` - New comprehensive application (1,103 lines)
- ✅ `crpm/discovery.py` - Multi-algorithm discovery (390 lines)
- ✅ `crpm/analytics.py` - Performance analytics (365 lines)
- ✅ `crpm/variants.py` - Variant analysis (385 lines)
- ✅ `crpm/visualization.py` - Plotly charts (340 lines)
- ✅ `crpm/dfg_utils.py` - DFG utilities (180 lines)
- ✅ `app_v1_backup.py` - Backup of original app

### Modified
- ✅ `crpm/conformance.py` - Fixed Optional import

### Preserved
- ✅ `app.py` - Original app still available (port 8501)
- ✅ All existing modules (`crpm/pipeline.py`, `crpm/conformance.py`)

---

## Testing Status

✅ **Application Running**: http://localhost:8502
✅ **Original App Preserved**: http://localhost:8501
✅ **No Breaking Changes**: All original functionality maintained
✅ **Backward Compatible**: Can switch between v1 and v2

### Tested Features
- ✅ XES log loading
- ✅ CSV upload and conversion
- ✅ Multi-algorithm discovery (Heuristics, Inductive, Alpha)
- ✅ Model visualization rendering
- ✅ Conformance computation (alignment + token replay)
- ✅ Performance analytics caching
- ✅ DFG discovery and filtering

---

## Next Steps (Optional Enhancements)

### 1. PDF Report Generation
- Compile all analysis results into a PDF
- Include model images, comparison tables, charts
- Executive summary with recommendations
- **Priority**: Medium (user requested)

### 2. Additional Discovery Algorithms
- Split Miner (balanced fitness/precision)
- ILP Miner (Integer Linear Programming)
- **Priority**: Low

### 3. Advanced Filtering
- Filter by variant conformance threshold
- Filter by activity presence/absence
- Custom trace filtering logic
- **Priority**: Low

### 4. Model Editing
- Interactive model refinement
- Add/remove transitions
- Modify dependencies
- **Priority**: Low

### 5. Real-time Monitoring
- Stream processing for live logs
- Continuous conformance monitoring
- Drift detection
- **Priority**: Very Low

---

## Deployment Instructions

### To Use New Version (Recommended)
```bash
# Stop old app (if running)
# <Ctrl+C> in terminal or close browser tab

# Run new version
python -m streamlit run app_v2.py
# or
streamlit run app_v2.py
```

### To Permanently Replace Old Version
```bash
# Backup original
mv app.py app_v1_backup.py

# Rename new version
mv app_v2.py app.py

# Run normally
streamlit run app.py
```

### To Run Both Versions Simultaneously
```bash
# Terminal 1: Original app
streamlit run app.py --server.port 8501

# Terminal 2: New app
streamlit run app_v2.py --server.port 8502
```

---

## Dependencies

All features use existing dependencies:
- streamlit==1.47.1
- pm4py==2.7.16
- pandas==2.3.1
- numpy==2.3.2
- plotly==6.2.0
- matplotlib==3.10.3
- lxml==6.0.0

No additional packages required!

---

## Conclusion

The CRPM v2.0 application successfully delivers:
✅ Multi-algorithm discovery with sensitivity analysis
✅ Comprehensive performance analytics with bottleneck detection
✅ Deep variant analysis with per-variant conformance
✅ Interactive DFG visualizations (frequency & performance)
✅ Professional model comparison with automated recommendations

The implementation is production-ready, fully cached for performance, and maintains backward compatibility with the original application.

**Access Points:**
- **Original App (v1)**: http://localhost:8501
- **New App (v2)**: http://localhost:8502

---

*Generated: 2025-10-20*
*CRPM v2.0 - Comprehensive Process Mining Workbench*
*Built with Streamlit + PM4Py 2.7.16 + Plotly 6.2.0*
