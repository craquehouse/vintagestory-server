/**
 * Server API functions for lifecycle management.
 *
 * These functions wrap the apiClient to provide typed access to
 * server management endpoints.
 */

import { apiClient } from './client';
import type {
  ApiResponse,
  ServerStatus,
  InstallStatus,
  ActionMessage,
} from './types';

const API_PREFIX = '/api/v1alpha1/server';

/**
 * Fetch the current server status.
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchServerStatus(): Promise<
  ApiResponse<ServerStatus>
> {
  return apiClient<ApiResponse<ServerStatus>>(`${API_PREFIX}/status`);
}

/**
 * Start the VintageStory server.
 *
 * Requires Admin role.
 */
export async function startServer(): Promise<ApiResponse<ActionMessage>> {
  return apiClient<ApiResponse<ActionMessage>>(`${API_PREFIX}/start`, {
    method: 'POST',
  });
}

/**
 * Stop the VintageStory server.
 *
 * Requires Admin role.
 */
export async function stopServer(): Promise<ApiResponse<ActionMessage>> {
  return apiClient<ApiResponse<ActionMessage>>(`${API_PREFIX}/stop`, {
    method: 'POST',
  });
}

/**
 * Restart the VintageStory server.
 *
 * Requires Admin role.
 */
export async function restartServer(): Promise<ApiResponse<ActionMessage>> {
  return apiClient<ApiResponse<ActionMessage>>(`${API_PREFIX}/restart`, {
    method: 'POST',
  });
}

/**
 * Install a specific version of the VintageStory server.
 *
 * Requires Admin role.
 *
 * @param version - The version to install (e.g., "1.21.3")
 */
export async function installServer(
  version: string
): Promise<ApiResponse<ActionMessage>> {
  return apiClient<ApiResponse<ActionMessage>>(`${API_PREFIX}/install`, {
    method: 'POST',
    body: { version },
  });
}

/**
 * Fetch the current installation status.
 *
 * Requires Admin role.
 */
export async function fetchInstallStatus(): Promise<
  ApiResponse<InstallStatus>
> {
  return apiClient<ApiResponse<InstallStatus>>(`${API_PREFIX}/install/status`);
}
