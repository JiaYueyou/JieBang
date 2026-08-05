import type { DataProvider } from "./provider";
import { httpDataProvider } from "./httpProvider";

// FYZ runtime always uses persisted backend data. Mock providers remain isolated
// test fixtures and are never selected by a production or development build.
export const providerMode = "http";
export const dataProvider: DataProvider = httpDataProvider;
