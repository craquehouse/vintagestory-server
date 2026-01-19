import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchGameConfig,
  updateGameSetting,
  fetchApiSettings,
  updateApiSetting,
  fetchConfigDirectories,
  fetchConfigFiles,
  fetchConfigFileContent,
} from './config';
import type {
  ApiResponse,
  GameConfigData,
  GameSettingUpdateData,
  ApiSettingsData,
  ApiSettingUpdateData,
  ConfigDirectoryListData,
  ConfigFileListData,
  ConfigFileContentData,
} from './types';

// Mock the API client
vi.mock('./client', () => ({
  apiClient: vi.fn(),
}));

import { apiClient } from './client';

describe('api/config', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('fetchGameConfig', () => {
    it('calls correct endpoint with GET method', async () => {
      const mockResponse: ApiResponse<GameConfigData> = {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'My Server',
              type: 'string',
              liveUpdate: false,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2026-01-18T10:00:00Z',
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchGameConfig();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/config/game');
      expect(result).toEqual(mockResponse);
    });

    it('returns game config data on success', async () => {
      const mockResponse: ApiResponse<GameConfigData> = {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'Port',
              value: 42420,
              type: 'int',
              liveUpdate: false,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2026-01-18T10:00:00Z',
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchGameConfig();

      expect(result.status).toBe('ok');
      expect(result.data.settings).toHaveLength(1);
      expect(result.data.settings[0].key).toBe('Port');
    });

    it('propagates errors from apiClient', async () => {
      const mockError = new Error('Network error');
      vi.mocked(apiClient).mockRejectedValue(mockError);

      await expect(fetchGameConfig()).rejects.toThrow('Network error');
    });
  });

  describe('updateGameSetting', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: ApiResponse<GameSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'ServerName',
          value: 'New Server Name',
          method: 'file_update',
          pendingRestart: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await updateGameSetting('ServerName', 'New Server Name');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/game/settings/ServerName',
        {
          method: 'POST',
          body: { value: 'New Server Name' },
        }
      );
    });

    it('encodes special characters in setting key', async () => {
      const mockResponse: ApiResponse<GameSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'Key/With/Slashes',
          value: 'test',
          method: 'file_update',
          pendingRestart: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await updateGameSetting('Key/With/Slashes', 'test');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/game/settings/Key%2FWith%2FSlashes',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('handles string values', async () => {
      const mockResponse: ApiResponse<GameSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'ServerName',
          value: 'Test Server',
          method: 'file_update',
          pendingRestart: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await updateGameSetting('ServerName', 'Test Server');

      expect(result.data.value).toBe('Test Server');
      expect(apiClient).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: { value: 'Test Server' },
        })
      );
    });

    it('handles number values', async () => {
      const mockResponse: ApiResponse<GameSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'Port',
          value: 42420,
          method: 'file_update',
          pendingRestart: true,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await updateGameSetting('Port', 42420);

      expect(apiClient).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: { value: 42420 },
        })
      );
    });

    it('handles boolean values', async () => {
      const mockResponse: ApiResponse<GameSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'EnablePvP',
          value: true,
          method: 'file_update',
          pendingRestart: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await updateGameSetting('EnablePvP', true);

      expect(apiClient).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: { value: true },
        })
      );
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Update failed'));

      await expect(updateGameSetting('ServerName', 'Test')).rejects.toThrow(
        'Update failed'
      );
    });
  });

  describe('fetchApiSettings', () => {
    it('calls correct endpoint with GET method', async () => {
      const mockResponse: ApiResponse<ApiSettingsData> = {
        status: 'ok',
        data: {
          settings: {
            autoStartServer: true,
            blockEnvManagedSettings: false,
            enforceEnvOnRestart: false,
            modListRefreshInterval: 300,
            serverVersionsRefreshInterval: 3600,
          },
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchApiSettings();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/config/api');
      expect(result).toEqual(mockResponse);
    });

    it('returns API settings data on success', async () => {
      const mockResponse: ApiResponse<ApiSettingsData> = {
        status: 'ok',
        data: {
          settings: {
            autoStartServer: false,
            blockEnvManagedSettings: false,
            enforceEnvOnRestart: true,
            modListRefreshInterval: 600,
            serverVersionsRefreshInterval: 7200,
          },
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchApiSettings();

      expect(result.status).toBe('ok');
      expect(result.data.settings.autoStartServer).toBe(false);
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Forbidden'));

      await expect(fetchApiSettings()).rejects.toThrow('Forbidden');
    });
  });

  describe('updateApiSetting', () => {
    it('calls correct endpoint with POST method', async () => {
      const mockResponse: ApiResponse<ApiSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'auto_start_server',
          value: false,
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await updateApiSetting('auto_start_server', false);

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/api/settings/auto_start_server',
        {
          method: 'POST',
          body: { value: false },
        }
      );
    });

    it('encodes special characters in setting key', async () => {
      const mockResponse: ApiResponse<ApiSettingUpdateData> = {
        status: 'ok',
        data: {
          key: 'key with spaces',
          value: 'test',
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await updateApiSetting('key with spaces', 'test');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/api/settings/key%20with%20spaces',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('handles string, number, and boolean values', async () => {
      const mockResponse: ApiResponse<ApiSettingUpdateData> = {
        status: 'ok',
        data: { key: 'test', value: 'value' },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      // String
      await updateApiSetting('string_key', 'string_value');
      expect(apiClient).toHaveBeenLastCalledWith(
        expect.any(String),
        expect.objectContaining({ body: { value: 'string_value' } })
      );

      // Number
      await updateApiSetting('number_key', 123);
      expect(apiClient).toHaveBeenLastCalledWith(
        expect.any(String),
        expect.objectContaining({ body: { value: 123 } })
      );

      // Boolean
      await updateApiSetting('boolean_key', true);
      expect(apiClient).toHaveBeenLastCalledWith(
        expect.any(String),
        expect.objectContaining({ body: { value: true } })
      );
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Unauthorized'));

      await expect(updateApiSetting('test', 'value')).rejects.toThrow(
        'Unauthorized'
      );
    });
  });

  describe('fetchConfigDirectories', () => {
    it('calls endpoint without directory parameter', async () => {
      const mockResponse: ApiResponse<ConfigDirectoryListData> = {
        status: 'ok',
        data: {
          directories: ['Mods', 'ModConfig', 'Saves'],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchConfigDirectories();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/config/directories');
      expect(result.data.directories).toEqual(['Mods', 'ModConfig', 'Saves']);
    });

    it('calls endpoint with directory parameter', async () => {
      const mockResponse: ApiResponse<ConfigDirectoryListData> = {
        status: 'ok',
        data: {
          directories: ['subfolder1', 'subfolder2'],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchConfigDirectories('Mods');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/directories?directory=Mods'
      );
    });

    it('encodes special characters in directory parameter', async () => {
      const mockResponse: ApiResponse<ConfigDirectoryListData> = {
        status: 'ok',
        data: { directories: [] },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchConfigDirectories('path/with/slashes');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/directories?directory=path%2Fwith%2Fslashes'
      );
    });

    it('handles empty directory list', async () => {
      const mockResponse: ApiResponse<ConfigDirectoryListData> = {
        status: 'ok',
        data: {
          directories: [],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchConfigDirectories();

      expect(result.data.directories).toEqual([]);
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Directory not found'));

      await expect(fetchConfigDirectories('invalid')).rejects.toThrow(
        'Directory not found'
      );
    });
  });

  describe('fetchConfigFiles', () => {
    it('calls endpoint without directory parameter', async () => {
      const mockResponse: ApiResponse<ConfigFileListData> = {
        status: 'ok',
        data: {
          files: ['serverconfig.json', 'allowedmods.json'],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchConfigFiles();

      expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/config/files');
      expect(result.data.files).toHaveLength(2);
    });

    it('calls endpoint with directory parameter', async () => {
      const mockResponse: ApiResponse<ConfigFileListData> = {
        status: 'ok',
        data: {
          files: ['config.json'],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchConfigFiles('ModConfig');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/files?directory=ModConfig'
      );
    });

    it('encodes special characters in directory parameter', async () => {
      const mockResponse: ApiResponse<ConfigFileListData> = {
        status: 'ok',
        data: { files: [] },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchConfigFiles('dir/with/special chars');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/files?directory=dir%2Fwith%2Fspecial%20chars'
      );
    });

    it('handles empty file list', async () => {
      const mockResponse: ApiResponse<ConfigFileListData> = {
        status: 'ok',
        data: {
          files: [],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchConfigFiles();

      expect(result.data.files).toEqual([]);
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Access denied'));

      await expect(fetchConfigFiles('restricted')).rejects.toThrow(
        'Access denied'
      );
    });
  });

  describe('fetchConfigFileContent', () => {
    it('calls correct endpoint with encoded filename', async () => {
      const mockResponse: ApiResponse<ConfigFileContentData> = {
        status: 'ok',
        data: {
          filename: 'serverconfig.json',
          content: { ServerName: 'My Server', Port: 42420 },
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchConfigFileContent('serverconfig.json');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/files/serverconfig.json'
      );
      expect(result.data.content).toEqual({
        ServerName: 'My Server',
        Port: 42420,
      });
    });

    it('encodes special characters in filename', async () => {
      const mockResponse: ApiResponse<ConfigFileContentData> = {
        status: 'ok',
        data: { filename: 'file with spaces.json', content: {} },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchConfigFileContent('file with spaces.json');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/files/file%20with%20spaces.json'
      );
    });

    it('encodes slashes in filename', async () => {
      const mockResponse: ApiResponse<ConfigFileContentData> = {
        status: 'ok',
        data: { filename: 'path/to/file.json', content: {} },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      await fetchConfigFileContent('path/to/file.json');

      expect(apiClient).toHaveBeenCalledWith(
        '/api/v1alpha1/config/files/path%2Fto%2Ffile.json'
      );
    });

    it('returns parsed JSON content', async () => {
      const mockResponse: ApiResponse<ConfigFileContentData> = {
        status: 'ok',
        data: {
          filename: 'config.json',
          content: {
            setting1: 'value1',
            setting2: 123,
            setting3: true,
            nested: { key: 'value' },
          },
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const result = await fetchConfigFileContent('config.json');

      expect(result.data.content).toHaveProperty('setting1', 'value1');
      expect(result.data.content).toHaveProperty('setting2', 123);
      expect(result.data.content).toHaveProperty('setting3', true);
      expect(result.data.content).toHaveProperty('nested');
    });

    it('propagates errors from apiClient', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('File not found'));

      await expect(
        fetchConfigFileContent('nonexistent.json')
      ).rejects.toThrow('File not found');
    });
  });

  describe('API prefix constant', () => {
    it('uses consistent API prefix across all endpoints', async () => {
      const mockResponse = { status: 'ok' as const, data: {} as any };
      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      // Call all functions
      await fetchGameConfig();
      await updateGameSetting('key', 'value');
      await fetchApiSettings();
      await updateApiSetting('key', 'value');
      await fetchConfigDirectories();
      await fetchConfigFiles();
      await fetchConfigFileContent('file.json');

      // All calls should start with /api/v1alpha1/config
      const calls = vi.mocked(apiClient).mock.calls;
      calls.forEach(([url]) => {
        expect(url).toMatch(/^\/api\/v1alpha1\/config/);
      });
    });
  });
});
