# AI Novel Generation Agent System - Functional Requirements Document

## Document Overview

This document defines the core functional requirements and performance requirements for the AI Novel Generation Agent System, focusing on multi-angle robustness, functional completeness, and performance.

## 1. Core Functional Requirements

### 1.1 Multi-Agent Collaborative Workflow

#### 1.1.1 Agent Responsibilities and Functions

##### **TrendAgent (Trend Analysis Agent)**
**Core Functions**:
- Real-time crawling or accessing novel platform hot lists
- Analyzing current popular genre distribution
- Statistical analysis of reader preferences
- Market trend prediction and potential题材 identification
- Chapter count recommendations based on historical data

**Outputs**:
- `trend_analysis.json`: Structured trend analysis report
- Hot genre rankings and heat indices
- Reader profile analysis
- Chapter count recommendations
- Market saturation analysis
- Trend predictions

**Robustness Design**:
- Data caching: 24-hour cache for identical queries
- Fallback strategy: Use historical baseline data when external sources unavailable
- Data validation: Integrity checks and deduplication
- Rate limiting: Avoid triggering anti-crawling mechanisms

##### **StyleAgent (Style Analysis Agent)**
**Core Functions**:
- Deep analysis of target novel's language style features
- Extraction of narrative rhythm patterns
- Analysis of character dialogue styles and description characteristics
- Identification of emotional expression methods and rhetorical devices
- Establishment of quantifiable style parameter system

**Outputs**:
- `style_parameters.json`: Quantified style configuration file
- Language complexity score (1-10)
- Narrative rhythm parameters
- Dialogue proportion and style features
- Description detail level and sensory dimension distribution
- Emotional intensity curves and turning point patterns
- Rhetorical device usage frequency statistics

**Robustness Design**:
- Multi-sample analysis: Ensure style consistency across chapters
- Anomaly detection: Identify style突变 points
- Parameter standardization: Convert subjective styles to quantifiable parameters
- Template matching: Support predefined style templates

##### **PlannerAgent (Planning Agent) - 3-Chapter Batch Review Mechanism**
**Core Functions**:
- **Story Outline Generation**:
  - Determine core题材 and theme based on trend analysis
  - Design complete three-act story structure
  - Build main character relationship networks and growth arcs
  - Design core conflicts and矛盾 resolution paths
  - Plan emotional curves and reader engagement points

- **Chapter Outline Generation (3-Chapter Batches)**:
  - First generate complete outline for first 3 chapters
  - Deep review of first 3 chapters, solidify settings upon approval
  - Generate subsequent 3-chapter batches based on solidified settings
  - Rolling generation until all chapters completed

**3-Chapter Batch Review Mechanism**:
```
Generate first 3 chapters → Deep review → Approved? → Yes → Solidify settings → Generate next 3 chapters
                              ↓No
                       Targeted revision → Re-review → Loop count+1
                              ↓
                     Loop count>3? → Yes → Adjust strategy or manual intervention
                              ↓No
                       Continue revision loop
```

**Batch Solidification Content**:
1. **Core Setting Solidification**:
   - Main character personalities and behavior patterns
   - Worldview foundation rules and settings
   - Core conflicts and矛盾 foundation
   - Story tone and emotional基调

2. **Plot Framework Solidification**:
   - Specific plot development of first 3 chapters
   - Initial character relationship states
   - Suspense setup and foreshadowing arrangements
   - Rhythm patterns and narrative styles

3. **Technical Parameter Solidification**:
   - Chapter length standards (e.g., 3000±500 words per chapter)
   - Dialogue proportion range (e.g., 20-40%)
   - Description detail level standards
   - Emotional intensity baselines

**Review Quantification Standards** (First 3-Chapter Batch):
1. **Structural Integrity Score** (Weight 30%):
   - Three-act structure completeness: ≥85%
   - Plot progression logic: ≥90%
   - Suspense setup effectiveness: ≥80%
   - Emotional curve rationality: ≥75%

2. **Character Consistency Score** (Weight 25%):
   - Main character personality stability: ≥95%
   - Character behavior rationality: ≥90%
   - Relationship development naturalness: ≥85%
   - Growth arc clarity: ≥80%

3. **Market Fit Score** (Weight 20%):
   - Genre heat match: ≥70%
   - Reader preference符合度: ≥75%
   - Innovation balance: ≥65%
   - Commercial potential assessment: ≥60%

4. **Technical Feasibility Score** (Weight 15%):
   - Chapter writability assessment: ≥90%
   - Complexity controllability: ≥85%
   - Expansion potential assessment: ≥80%
   - Resource requirement rationality: ≥75%

5. **Style Compliance Score** (Weight 10%):
   - Style parameter match: ≥85%
   - Narrative rhythm appropriateness: ≥80%
   - Language style consistency: ≥90%

**Passing Threshold**:
- Total score ≥80 points (100-point scale)
- Each dimension ≥60 points (avoid严重短板)
- Structural integrity and character consistency must ≥70 points

##### **WriterAgent (Writing Agent) - 3-Chapter Batch Generation Mechanism**
**Core Functions**:
- **Chapter Content Generation (3-Chapter Batches)**:
  - Each 3 chapters as one generation batch
  - Parallel generation of 3 chapters within batch
  - Intra-batch review ensures consistency
  - Solidify content upon approval, roll to next batch

**3-Chapter Batch Generation Process**:
```
Batch preparation → 3-chapter parallel generation → Intra-batch review → Problem revision → Content solidification → Next batch
```

**Intra-Batch Review Quantification Standards**:
1. **Plot Coherence** (Weight 40%):
   - Chapter 1→2 plot connection: ≥90%
   - Chapter 2→3 plot development rationality: ≥85%
   - 3-chapter overall plot progression logic: ≥80%

2. **Character Consistency** (Weight 30%):
   - Main character personality stability (within 3 chapters): ≥95%
   - Character behavior pattern consistency: ≥90%
   - Dialogue style personalization stability: ≥85%

3. **Style Consistency** (Weight 20%):
   - Language style uniformity (within 3 chapters): ≥90%
   - Narrative rhythm stability: ≥85%
   - Description detail consistency: ≥80%

4. **Language Quality** (Weight 10%):
   - Grammar correctness rate: ≥98%
   - Expression clarity score: ≥85 points
   - Vocabulary richness (unique word proportion): ≥15%

**Passing Threshold** (3-Chapter Batch):
- Batch total score: ≥75 points (100-point scale)
- Single chapter minimum score: ≥65 points
- Key dimensions: Plot ≥70 points, Character ≥75 points
- Problem density: Severe problems ≤1/chapter, Important problems ≤3/chapter

##### **PolishAgent (Polishing Agent)**
**Core Functions**:
- **Language Optimization**:
  - Correct grammar errors and inappropriate expressions
  - Optimize sentence structure and paragraph organization
  - Improve language fluency and readability
  - Unify terminology and expressions

- **Style Enhancement**:
  - Strengthen consistency with设定 styles
  - Adjust rhetorical device usage frequency
  - Optimize emotional expression intensity
  - Improve narrative rhythm sense

**Polishing Mechanism**:
1. **Grammar Check Layer**: Basic language error correction
2. **Expression Optimization Layer**: Sentence restructuring and vocabulary replacement
3. **Style Adjustment Layer**: Strengthen style feature consistency
4. **Rhythm Optimization Layer**: Adjust narrative rhythm and paragraph division

**Outputs**:
- `ch_01_polished.md` ~ `ch_NN_polished.md`: Polished chapters
- `polish_report.json`: Polishing modification records and statistics

**Robustness Design**:
- Conservative modifications: Ensure core content unchanged
- Version comparison: Keep before/after modification records
- Quality assessment: Automatic improvement effect evaluation after polishing

##### **AuditorAgent (Audit Agent)**
**Core Functions**:

**Audit Dimension System**:
1. **Plot Coherence Audit**:
   - Check logical rationality of plot development
   - Verify cause-effect relationships between plots
   - Identify plot漏洞 and矛盾 points
   - Evaluate suspense setup and resolution effectiveness

2. **Character Consistency Audit**:
   - Verify character behavior consistency with personality settings
   - Check rationality of character relationship development
   - Identify character image崩塌 or突变
   - Evaluate completeness of character growth arcs

3. **Logical Rationality Audit**:
   - Check internal consistency of worldview settings
   - Verify probability and rationality of event occurrences
   - Identify常识 errors and logical漏洞
   - Evaluate credibility of plot development

4. **Style Compliance Audit**:
   - Quantitatively evaluate match with设定 styles
   - Check language style consistency
   - Verify narrative rhythm compliance
   - Evaluate appropriateness of emotional expression

5. **Language Quality Audit**:
   - Check grammar correctness and expression clarity
   - Evaluate vocabulary richness and appropriateness
   - Identify重复 expressions and redundant content
   - Evaluate overall readability and fluency

**Audit Quantification Indicators**:
- Plot coherence: Accuracy ≥95%, Recall ≥90%
- Character consistency: Accuracy ≥92%, Recall ≥88%
- Style compliance: Similarity ≥85%
- Language quality: Grammar correctness rate ≥98%

##### **ReviserAgent (Revision Agent)**
**Core Functions**:

**Revision Strategy System**:
1. **Problem-Oriented Revision**:
   - Target specific problem points in audit reports
   - Apply corresponding revision strategies and templates
   - Ensure fundamental problem resolution

2. **Incremental Revision Principle**:
   - Minimize modification scope, preserve effective content
   - Avoid complete rewriting, improve revision efficiency
   - Ensure smooth transition before/after revision

**Revision Quantification Indicators**:
- Severe problem resolution rate: 100%
- Important problem resolution rate: ≥80%
- Single revision quality improvement: ≥5 points (100-point scale)
- Minor problem revision time: <30 seconds/problem
- Medium problem revision time: <90 seconds/problem
- Severe problem revision time: <180 seconds/problem

### 1.2 Performance Requirements

#### 1.2.1 3-Chapter Batch Performance Indicators

**Planning Phase Performance**:
- First 3-chapter outline generation and review: 8 minutes
- Subsequent每3-chapter outline generation: 5 minutes
- 18-chapter planning total time: 33 minutes

**Writing Phase Performance**:
- Single batch (3 chapters) generation and review: 6.5 minutes
- Inter-batch coordination: 1 minute
- 18-chapter writing total time: 45 minutes

**Overall Process Performance**:
- Optimal scenario (no major revisions): 88 minutes
- Average scenario (moderate revisions): 105 minutes
- Worst scenario (multiple revisions): 135 minutes
- Efficiency improvement vs traditional single-chapter review: 30%

#### 1.2.2 Resource Usage Optimization

**CPU Utilization**:
- Average utilization: 55-65%
- Peak utilization (batch generation): <80%
- Idle period utilization: 30-40%

**Memory Usage**:
- Base memory: 300MB (system + framework)
- Peak during batch generation: 650MB (including 3-chapter context)
- Minimum between batches: 350MB (after cleanup)
- Average memory usage: 450MB

**Efficiency Improvement Quantification**:
1. **Time Efficiency**:
   - Single-chapter serial review: Estimated 150 minutes
   - 3-chapter batch review: Actual 105 minutes
   - Efficiency improvement: 30%

2. **Quality Stability**:
   - Early problem detection rate: Improved from 60% to 85%
   - Problem扩散 control: Batch isolation reduces problem impact scope
   - Consistency保障: Solidification mechanism ensures前后 consistency

## 2. Key Innovations

### 2.1 3-Chapter Batch Review Mechanism
- **Batch Division**: Each 3 chapters as one review unit
- **Solidification Mechanism**: Approved content immediately solidified
- **Rolling Generation**: Generate subsequent batches based on solidified content
- **Problem Isolation**: Inter-batch problem isolation prevents扩散

### 2.2 Quantification Control System
- **Creation Quantification**: Chapter structure, component proportions, information density
- **Review Quantification**: Accuracy, recall, coverage
- **Revision Quantification**: Resolution rate, improvement degree, efficiency
- **Performance Quantification**: Time indicators, resource indicators, efficiency indicators

### 2.3 Robustness Design
- **Error Recovery**: Automatic retry, fallback strategies, state recovery
- **Data Consistency**: Solidification mechanism, version management, integrity checks
- **Resource Management**: Batch cleanup, memory optimization, IO batch processing

## 3. Document Notes

1. This document focuses on system functional requirements and performance requirements
2. All requirements consider multi-angle robustness
3. Performance requirements结合 actual business scenarios
4. Functional requirements详细 describe specific requirements and acceptance criteria for each function point

---
**Document Version**: 1.2  
**Update Date**: 2026-03-26  
**Update Content**: Implemented 3-chapter batch review mechanism, added detailed quantification data