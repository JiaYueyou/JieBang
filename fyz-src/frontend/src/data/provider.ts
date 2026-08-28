import type {
  AdminOverview, AdminResourceSnapshot, AgentRunAuditPage, AgentRunStatus, CapabilityChange, CareerRecommendation, CrawlerAutomationConfig, DashboardOverview, DashboardQuery, JobImportResult, PipelineRun,
  DataQualityPage, DataQualityQuery, RawJobQualityItem,
  EmergingJob, FavoriteRecord, FavoriteTargetType, GraphAsyncTask, GraphEnrichmentCandidate, GraphEnrichmentCandidatePage, GraphQuery, GraphSubgraph, HistoryInsights,
  HistoryRecord, JobCreatePayload, JobSummary, GenerateJDRequest, GeneratedJDDraft, JDInputSuggestion, JDInputSuggestionRequest, TalentSummary, TrendOverview, TrendQuery, AnalysisDataQuality, AnalysisBaseline, JobReferenceStandardPage,
  EnterpriseDepartment, EnterpriseDepartmentInput, EnterpriseEmployeeDirectory, EnterpriseEmployeeDirectoryInput, EnterpriseTalent, EnterpriseTalentCreate, InternalMatchResult, InternalPosition, InternalPositionCreate,
  SkillDemandSummary, SkillFactReviewItem, SkillFactReviewPage,
  SkillFactVerificationStatus, TransferDecision, TransferRuleSet, TransferRuleSetCreate,
  ResumeAdmissionPayload,
  ObservedJobDetail, ObservedJobPage, PageResult,
} from "@/domain/types";

export interface DataProvider {
  dashboard: { getOverview(query?: DashboardQuery): Promise<DashboardOverview> };
  jobs: {
    list(query?: { page?: number; pageSize?: number; status?: JobSummary["status"]; keyword?: string }): Promise<PageResult<JobSummary>>;
    listObserved(query: {
      page: number;
      pageSize: number;
      keyword?: string;
      city?: string;
      source?: string;
    }): Promise<ObservedJobPage>;
    getObserved(id: number): Promise<ObservedJobDetail>;
    getInsights(skill?: string): Promise<{ emergingJobs: EmergingJob[]; capabilityChanges: CapabilityChange[]; dataQuality: AnalysisDataQuality; baseline: AnalysisBaseline }>;
    decideInsight(id: number, decision: "confirmed" | "ignored" | "planned", note?: string): Promise<void>;
    suggestJDInput(input: JDInputSuggestionRequest): Promise<JDInputSuggestion>;
    generateJD(input: GenerateJDRequest): Promise<GeneratedJDDraft>;
    create(job: JobCreatePayload): Promise<JobSummary>;
    update(job: JobSummary): Promise<JobSummary>;
    remove(id: number): Promise<void>;
    updateStatus(id: number, status: JobSummary["status"]): Promise<JobSummary>;
  };
  talents: {
    list(): Promise<TalentSummary[]>;
    get(resumeId: number): Promise<TalentSummary | null>;
    getDetails(resumeId: number): Promise<import("@/domain/types").TalentDetail>;
    updateDetails(resumeId: number, input: import("@/domain/types").TalentUpdatePayload): Promise<import("@/domain/types").TalentDetail>;
    upload(input: import("@/domain/types").ResumeUploadPayload): Promise<void>;
    download(resumeId: number, filename: string): Promise<void>;
    preview(resumeId: number): Promise<{ url: string; contentType: string }>;
    matchJobs(resumeId: number, jobIds: number[]): Promise<import("@/domain/types").TalentMatch[]>;
    recalculate(): Promise<{ resumes_processed: number; matches_upserted: number }>;
    explain(matchId: number, onProgress?: (progress: number, status: string) => void): Promise<import("@/domain/types").MatchExplanation>;
  };
  career: { analyze(input: {
    skillText: string;
    enterpriseTech: string;
    enterpriseJobs: string[];
    targetJobIds?: number[];
    resumeFiles?: File[];
    enterpriseFiles?: File[];
  }): Promise<import("@/domain/types").CareerAnalysisResult>;
  recover(): Promise<import("@/domain/types").CareerAnalysisResult | null>;
  };
  internalTransfer: {
    searchEmployeeDirectory(keyword: string, department?: string): Promise<EnterpriseEmployeeDirectory[]>;
    listDepartments(): Promise<EnterpriseDepartment[]>;
    createDepartment(input: EnterpriseDepartmentInput): Promise<EnterpriseDepartment>;
    updateDepartment(id: number, input: EnterpriseDepartmentInput): Promise<EnterpriseDepartment>;
    removeDepartment(id: number): Promise<void>;
    createEmployee(input: EnterpriseEmployeeDirectoryInput): Promise<EnterpriseEmployeeDirectory>;
    updateEmployee(id: number, input: EnterpriseEmployeeDirectoryInput): Promise<EnterpriseEmployeeDirectory>;
    removeEmployee(id: number): Promise<void>;
    createTalentFromDirectory(employeeId: number): Promise<EnterpriseTalent>;
    admitResume(resumeId: number, input: ResumeAdmissionPayload): Promise<EnterpriseTalent>;
    listPositions(): Promise<InternalPosition[]>;
    listPositionsPage(query: { page: number; pageSize: number; status?: InternalPosition["status"]; keyword?: string }): Promise<PageResult<InternalPosition>>;
    createPosition(input: InternalPositionCreate): Promise<InternalPosition>;
    updatePositionStatus(id: number, status: InternalPosition["status"]): Promise<InternalPosition>;
    listTalents(): Promise<EnterpriseTalent[]>;
    createTalent(input: EnterpriseTalentCreate): Promise<EnterpriseTalent>;
    listSkillDemands(): Promise<SkillDemandSummary[]>;
    listRuleSets(): Promise<TransferRuleSet[]>;
    createRuleSet(input: TransferRuleSetCreate): Promise<TransferRuleSet>;
    getRuleSet(id: number): Promise<TransferRuleSet>;
    updateRuleSet(id: number, input: TransferRuleSetCreate): Promise<TransferRuleSet>;
    removeRuleSet(id: number): Promise<void>;
    matchByTalent(input: { talent_id: number; position_ids?: number[]; rule_set_id?: number }): Promise<InternalMatchResult[]>;
    matchByPosition(input: { position_id: number; talent_ids?: number[]; rule_set_id?: number }): Promise<InternalMatchResult[]>;
    listDecisions(): Promise<TransferDecision[]>;
    createDecision(input: { talent_id: number; position_id: number; rule_set_id?: number; note?: string }): Promise<TransferDecision>;
  };
  graph: {
    getOverview(query?: GraphQuery): Promise<GraphSubgraph>;
    getNeighbors(nodeId: string, query?: { cursor?: string; pageSize?: number; maxLayer?: 1 | 2 | 3 | 4 | 5 }): Promise<GraphSubgraph>;
    getPanorama(query?: GraphQuery): Promise<GraphSubgraph>;
    getNode(nodeId: string): Promise<GraphSubgraph>;
    expand(nodeId: string, depth?: number): Promise<GraphSubgraph>;
    search(query: string, type?: string): Promise<GraphSubgraph>;
    path(fromId: string, toId: string): Promise<GraphSubgraph>;
      sync(): Promise<{ node_count: number; edge_count: number; fact_count: number }>;
      generateEnrichment(): Promise<{ node_count: number; edge_count: number; fact_count: number }>;
      startSync(): Promise<GraphAsyncTask>;
      startEnrichment(): Promise<GraphAsyncTask>;
      startPublication(candidateIds?: number[]): Promise<GraphAsyncTask>;
      getTask(taskId: string): Promise<GraphAsyncTask>;
    listEnrichment(query?: { page?: number; pageSize?: number; reviewStatus?: string }): Promise<GraphEnrichmentCandidatePage>;
    reviewEnrichment(candidateId: number, input: { action: "approve" | "reject"; note?: string; lockVersion: number }): Promise<GraphEnrichmentCandidate>;
    rejectMachineFailedEnrichment(): Promise<{ rejected_count: number; candidate_ids: number[] }>;
    publishEnrichment(candidateIds?: number[]): Promise<{ node_count: number; edge_count: number; fact_count: number }>;
  };
  trends: {
    getOverview(query: TrendQuery): Promise<TrendOverview>;
    listReferenceStandards(query: { page: number; pageSize: number; keyword?: string; stack?: string }): Promise<JobReferenceStandardPage>;
  };
  skillReviews: {
    list(query: {
      page: number;
      pageSize: number;
      status?: SkillFactVerificationStatus;
      keyword?: string;
    }): Promise<SkillFactReviewPage>;
    review(
      factId: number,
      decision: Exclude<SkillFactVerificationStatus, "unverified">,
      note?: string,
    ): Promise<SkillFactReviewItem>;
    reviewBatch(
      factIds: number[],
      decision: Exclude<SkillFactVerificationStatus, "unverified">,
      note?: string,
    ): Promise<{ processed_count: number; skipped_count: number; fact_ids: number[] }>;
    approveAll(keyword?: string): Promise<{ processed_count: number; skipped_count: number; fact_ids: number[] }>;
  };
  favorites: {
    list(): Promise<FavoriteRecord[]>;
    toggle(type: FavoriteTargetType, targetId: number, title?: string): Promise<boolean>;
    removeMany(ids: number[]): Promise<void>;
    updateNote(id: number, note: string): Promise<void>;
  };
  history: {
    list(): Promise<HistoryRecord[]>;
    record(input: Omit<HistoryRecord, "id" | "dateKey" | "date" | "time" | "badge">): Promise<HistoryRecord>;
    remove(id: number): Promise<void>;
    clear(): Promise<void>;
    getInsights(): Promise<HistoryInsights>;
  };
  admin: {
    getOverview(): Promise<AdminOverview>;
    getResources(): Promise<AdminResourceSnapshot>;
    listAgentRuns(query: {
      page: number;
      pageSize: number;
      agentType?: string;
      status?: AgentRunStatus;
    }): Promise<AgentRunAuditPage>;
    listQuality(query: DataQualityQuery): Promise<DataQualityPage>;
    decideQuality(
      id: number,
      action: "exclude" | "restore",
      reason?: string,
    ): Promise<RawJobQualityItem>;
    toggleCrawler(id: number): Promise<void>;
    runCrawler(id: number): Promise<void>;
    startPipeline(sourceIds?: number[]): Promise<PipelineRun>;
    getPipelineRun(id: string): Promise<PipelineRun>;
    getCrawlerAutomation(): Promise<CrawlerAutomationConfig>;
    saveCrawlerAutomation(config: CrawlerAutomationConfig): Promise<CrawlerAutomationConfig>;
    pollCrawler(id: number): Promise<any>;
    importCrawlerOutput(filename: string): Promise<JobImportResult>;
  };
}
