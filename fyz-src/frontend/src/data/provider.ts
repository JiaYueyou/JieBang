import type {
  AdminOverview, CapabilityChange, CareerRecommendation, DashboardOverview,
  EmergingJob, FavoriteRecord, FavoriteTargetType, GraphQuery, GraphSubgraph, HistoryInsights,
  HistoryRecord, JobSummary, TalentSummary, TrendOverview,
} from "@/domain/types";

export interface DataProvider {
  dashboard: { getOverview(): Promise<DashboardOverview> };
  jobs: {
    list(): Promise<JobSummary[]>;
    getInsights(): Promise<{ emergingJobs: EmergingJob[]; capabilityChanges: CapabilityChange[] }>;
    generateJD(input: Record<string, string>): Promise<JobSummary>;
    create(job: JobSummary): Promise<JobSummary>;
    update(job: JobSummary): Promise<JobSummary>;
    remove(id: number): Promise<void>;
    updateStatus(id: number, status: JobSummary["status"]): Promise<JobSummary>;
  };
  talents: { list(): Promise<TalentSummary[]>; get(resumeId: number): Promise<TalentSummary | null> };
  career: { analyze(input: { skillText: string; enterpriseJobs: string[] }): Promise<CareerRecommendation[]> };
  graph: {
    getPanorama(query?: GraphQuery): Promise<GraphSubgraph>;
    getNode(nodeId: string): Promise<GraphSubgraph>;
    expand(nodeId: string, depth?: number): Promise<GraphSubgraph>;
    search(query: string, type?: string): Promise<GraphSubgraph>;
    path(fromId: string, toId: string): Promise<GraphSubgraph>;
  };
  trends: { getOverview(): Promise<TrendOverview> };
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
    toggleUser(id: number): Promise<void>;
    saveSettings(settings: Record<string, any>): Promise<void>;
  };
}
