import type {
  AdminOverview, CapabilityChange, CareerRecommendation, DashboardOverview, JobImportResult,
  EmergingJob, FavoriteRecord, FavoriteTargetType, GraphQuery, GraphSubgraph, HistoryInsights,
  HistoryRecord, JobCreatePayload, JobSummary, GenerateJDRequest, GeneratedJDDraft, JDInputSuggestion, JDInputSuggestionRequest, TalentSummary, TrendOverview, TrendQuery, AnalysisDataQuality, AnalysisBaseline,
  EnterpriseEmployeeDirectory, EnterpriseTalent, EnterpriseTalentCreate, InternalMatchResult, InternalPosition, InternalPositionCreate,
  SkillDemandSummary, SkillFactReviewItem, SkillFactReviewPage,
  SkillFactVerificationStatus, TransferDecision, TransferRuleSet, TransferRuleSetCreate,
  ObservedJobDetail, ObservedJobPage,
} from "@/domain/types";

export interface DataProvider {
  dashboard: { getOverview(): Promise<DashboardOverview> };
  jobs: {
    list(): Promise<JobSummary[]>;
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
    upload(input: import("@/domain/types").ResumeUploadPayload): Promise<void>;
    download(resumeId: number, filename: string): Promise<void>;
    explain(matchId: number): Promise<import("@/domain/types").MatchExplanation>;
  };
  career: { analyze(input: {
    skillText: string;
    enterpriseTech: string;
    enterpriseJobs: string[];
    resumeFiles?: File[];
    enterpriseFiles?: File[];
  }): Promise<import("@/domain/types").CareerAnalysisResult> };
  internalTransfer: {
    searchEmployeeDirectory(keyword: string): Promise<EnterpriseEmployeeDirectory[]>;
    createTalentFromDirectory(employeeId: number): Promise<EnterpriseTalent>;
    listPositions(): Promise<InternalPosition[]>;
    createPosition(input: InternalPositionCreate): Promise<InternalPosition>;
    updatePositionStatus(id: number, status: InternalPosition["status"]): Promise<InternalPosition>;
    listTalents(): Promise<EnterpriseTalent[]>;
    createTalent(input: EnterpriseTalentCreate): Promise<EnterpriseTalent>;
    listSkillDemands(): Promise<SkillDemandSummary[]>;
    listRuleSets(): Promise<TransferRuleSet[]>;
    createRuleSet(input: TransferRuleSetCreate): Promise<TransferRuleSet>;
    matchByTalent(input: { talent_id: number; position_ids?: number[]; rule_set_id?: number }): Promise<InternalMatchResult[]>;
    matchByPosition(input: { position_id: number; talent_ids?: number[]; rule_set_id?: number }): Promise<InternalMatchResult[]>;
    listDecisions(): Promise<TransferDecision[]>;
    createDecision(input: { talent_id: number; position_id: number; rule_set_id?: number; note?: string }): Promise<TransferDecision>;
  };
  graph: {
    getPanorama(query?: GraphQuery): Promise<GraphSubgraph>;
    getNode(nodeId: string): Promise<GraphSubgraph>;
    expand(nodeId: string, depth?: number): Promise<GraphSubgraph>;
    search(query: string, type?: string): Promise<GraphSubgraph>;
    path(fromId: string, toId: string): Promise<GraphSubgraph>;
    sync(): Promise<{ node_count: number; edge_count: number; fact_count: number }>;
  };
  trends: { getOverview(query: TrendQuery): Promise<TrendOverview> };
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
  };
  favorites: {
    list(): Promise<FavoriteRecord[]>;
    toggle(type: FavoriteTargetType, targetId: number, title?: string): Promise<boolean>;
    removeMany(ids: number[]): Promise<void>;
    updateNote(id: number, note: string): Promise<void>;
  };
  history: {
    list(): Promise<HistoryRecord[]>;
    remove(id: number): Promise<void>;
    clear(): Promise<void>;
    getInsights(): Promise<HistoryInsights>;
  };
  admin: {
    getOverview(): Promise<AdminOverview>;
    toggleCrawler(id: number): Promise<void>;
    runCrawler(id: number): Promise<void>;
    pollCrawler(id: number): Promise<any>;
    importCrawlerOutput(filename: string): Promise<JobImportResult>;
  };
}
