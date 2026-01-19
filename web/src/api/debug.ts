/**
 * Debug API functions for runtime debug logging control.
 *
 * These functions wrap the apiClient to provide typed access to
 * debug toggle endpoints.
 *
 * VSS-c9o: Debug logging toggle UI
 */

import { apiClient } from './client';
import type { ApiResponse, DebugStatusData, DebugToggleData } from './types';

const API_PREFIX = '/api/v1alpha1/debug';

/**
 * Fetch current debug logging status.
 *
 * Requires Admin role.
 */
export async function fetchDebugStatus(): Promise<ApiResponse<DebugStatusData>> {
  return apiClient<ApiResponse<DebugStatusData>>(API_PREFIX);
}

/**
 * Enable debug logging at runtime.
 *
 * Requires Admin role.
 */
export async function enableDebug(): Promise<ApiResponse<DebugToggleData>> {
  return apiClient<ApiResponse<DebugToggleData>>(`${API_PREFIX}/enable`, {
    method: 'POST',
  });
}

/**
 * Disable debug logging at runtime.
 *
 * Requires Admin role.
 */
export async function disableDebug(): Promise<ApiResponse<DebugToggleData>> {
  return apiClient<ApiResponse<DebugToggleData>>(`${API_PREFIX}/disable`, {
    method: 'POST',
  });
}
