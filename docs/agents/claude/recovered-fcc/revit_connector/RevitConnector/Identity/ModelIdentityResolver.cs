using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using Autodesk.Revit.DB;
using Microsoft.Extensions.Logging;

namespace RevitConnector.Identity;

/// <summary>
/// Resolves Revit document identity to BIMSpend project identity.
/// Implements the hierarchical identity resolution rules.
/// </summary>
public class ModelIdentityResolver
{
    private readonly ILogger _logger;
    private readonly Dictionary<string, AdminMapping> _adminMappings = new();
    private readonly string _adminMappingsPath;

    public ModelIdentityResolver(string adminMappingsPath, ILogger logger)
    {
        _adminMappingsPath = adminMappingsPath;
        _logger = logger;
        LoadAdminMappings();
    }

    /// <summary>
    /// Resolve model identity for a document using priority hierarchy.
    /// </summary>
    public ModelIdentity Resolve(Document doc)
    {
        // Rule 1: Explicit Admin Mapping (highest priority)
        var adminMapping = FindAdminMapping(doc);
        if (adminMapping != null)
        {
            _logger.LogDebug("Resolved via admin mapping: {ProjectId}", adminMapping.ProjectId);
            return adminMapping.ModelIdentity;
        }

        // Rule 2: ACC Cloud Identity
        var accIdentity = TryResolveAccIdentity(doc);
        if (accIdentity != null)
        {
            _logger.LogDebug("Resolved via ACC identity");
            return accIdentity;
        }

        // Rule 3: Workshared Central Identity
        if (doc.IsWorkshared)
        {
            var centralIdentity = ResolveWorksharedCentral(doc);
            if (centralIdentity != null)
            {
                _logger.LogDebug("Resolved via workshared central");
                return centralIdentity;
            }
        }

        // Rule 4: Standalone File Identity
        if (!string.IsNullOrEmpty(doc.PathName) && File.Exists(doc.PathName))
        {
            var fileIdentity = ResolveStandaloneFile(doc);
            if (fileIdentity != null)
            {
                _logger.LogDebug("Resolved via standalone file");
                return fileIdentity;
            }
        }

        // Rule 5: Unsaved/New Document (lowest confidence)
        _logger.LogDebug("Resolved as unsaved document");
        return new ModelIdentity
        {
            Type = "unsaved",
            SessionDocumentId = Guid.NewGuid().ToString(),
            DocumentTitle = doc.Title,
        };
    }

    /// <summary>
    /// Resolve identity from a file path (for Save As remapping).
    /// </summary>
    public ModelIdentity ResolveFromPath(string filePath)
    {
        if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
        {
            return new ModelIdentity { Type = "unknown", DocumentTitle = Path.GetFileName(filePath) };
        }

        try
        {
            var info = BasicFileInfo.Extract(filePath);
            if (info.IsWorkshared && info.CentralGUID != null)
            {
                return new ModelIdentity
                {
                    Type = "workshared_central",
                    CentralPath = NormalizePath(info.CentralPath ?? filePath),
                    CentralGuid = info.CentralGUID.Value.ToString(),
                    DocumentTitle = Path.GetFileName(filePath),
                };
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to extract file info from {Path}", filePath);
        }

        // Fallback to standalone file
        return ResolveStandaloneFilePath(filePath);
    }

    private AdminMapping? FindAdminMapping(Document doc)
    {
        var centralGuid = GetCentralGuid(doc);
        var centralPath = NormalizePath(doc.GetWorksharingCentralModelPath()?.CentralPath ?? doc.PathName);
        var fileHash = ComputeFileHash(doc.PathName);

        foreach (var mapping in _adminMappings.Values.Where(m => m.IsActive))
        {
            // Match by central GUID (most reliable)
            if (!string.IsNullOrEmpty(mapping.ModelIdentity.CentralGuid) &&
                mapping.ModelIdentity.CentralGuid.Equals(centralGuid, StringComparison.OrdinalIgnoreCase))
            {
                return mapping;
            }

            // Match by normalized central path
            if (!string.IsNullOrEmpty(mapping.ModelIdentity.CentralPath) &&
                mapping.ModelIdentity.CentralPath.Equals(centralPath, StringComparison.OrdinalIgnoreCase))
            {
                return mapping;
            }

            // Match by file hash (for standalone)
            if (!string.IsNullOrEmpty(mapping.ModelIdentity.FileHash) &&
                mapping.ModelIdentity.FileHash.Equals(fileHash, StringComparison.OrdinalIgnoreCase))
            {
                return mapping;
            }
        }

        return null;
    }

    private ModelIdentity? TryResolveAccIdentity(Document doc)
    {
        // In production: use Autodesk Platform Services SDK to get ACC project/model IDs
        // For now, return null - requires APS integration
        return null;
    }

    private ModelIdentity? ResolveWorksharedCentral(Document doc)
    {
        try
        {
            var centralPath = doc.GetWorksharingCentralModelPath()?.CentralPath ?? doc.PathName;
            var centralGuid = GetCentralGuid(doc);

            if (string.IsNullOrEmpty(centralGuid) || centralGuid == Guid.Empty.ToString())
            {
                return null;
            }

            return new ModelIdentity
            {
                Type = "workshared_central",
                CentralPath = NormalizePath(centralPath),
                CentralGuid = centralGuid,
                DocumentTitle = doc.Title,
            };
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to resolve workshared central identity");
            return null;
        }
    }

    private ModelIdentity? ResolveStandaloneFile(Document doc)
    {
        return ResolveStandaloneFilePath(doc.PathName);
    }

    private ModelIdentity? ResolveStandaloneFilePath(string filePath)
    {
        try
        {
            var fileInfo = new FileInfo(filePath);
            var hash = ComputeFileHash(filePath);

            return new ModelIdentity
            {
                Type = "standalone_file",
                FilePath = NormalizePath(filePath),
                FileHash = $"sha256:{hash}",
                FileSizeBytes = fileInfo.Length,
                DocumentTitle = Path.GetFileName(filePath),
            };
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to resolve standalone file identity for {Path}", filePath);
            return null;
        }
    }

    private string GetCentralGuid(Document doc)
    {
        try
        {
            var info = BasicFileInfo.Extract(doc.PathName);
            return info.CentralGUID?.ToString() ?? Guid.Empty.ToString();
        }
        catch
        {
            return Guid.Empty.ToString();
        }
    }

    private string NormalizePath(string path)
    {
        if (string.IsNullOrEmpty(path)) return path;

        try
        {
            // Normalize UNC paths and drive letters
            var fullPath = Path.GetFullPath(path);
            return fullPath.ToUpperInvariant(); // Case normalization for Windows
        }
        catch
        {
            return path.ToUpperInvariant();
        }
    }

    private string ComputeFileHash(string filePath)
    {
        if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
            return "";

        try
        {
            using var sha256 = SHA256.Create();
            using var stream = File.OpenRead(filePath);

            // For large files: hash first 64KB + last 64KB + file size
            const int chunkSize = 64 * 1024;
            var fileSize = stream.Length;

            if (fileSize <= chunkSize * 2)
            {
                var hash = sha256.ComputeHash(stream);
                return Convert.ToHexString(hash).ToLowerInvariant();
            }

            // Read first chunk
            var buffer = new byte[chunkSize];
            stream.ReadExactly(buffer, 0, chunkSize);
            sha256.TransformBlock(buffer, 0, chunkSize, null, 0);

            // Read last chunk
            stream.Seek(-chunkSize, SeekOrigin.End);
            stream.ReadExactly(buffer, 0, chunkSize);
            sha256.TransformFinalBlock(buffer, 0, chunkSize);

            // Include file size in hash
            var sizeBytes = BitConverter.GetBytes(fileSize);
            sha256.TransformFinalBlock(sizeBytes, 0, sizeBytes.Length);

            return Convert.ToHexString(sha256.Hash!).ToLowerInvariant();
        }
        catch
        {
            return "";
        }
    }

    private void LoadAdminMappings()
    {
        if (!File.Exists(_adminMappingsPath))
        {
            _logger.LogInformation("No admin mappings file found at {Path}", _adminMappingsPath);
            CreateSampleMappingsFile();
            return;
        }

        try
        {
            var json = File.ReadAllText(_adminMappingsPath);
            var data = JsonSerializer.Deserialize<AdminMappingsFile>(json, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
            });

            if (data?.Mappings != null)
            {
                foreach (var mapping in data.Mappings.Where(m => m.IsActive))
                {
                    _adminMappings[mapping.MappingId] = mapping;
                }
                _logger.LogInformation("Loaded {Count} admin mappings", _adminMappings.Count);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load admin mappings");
        }
    }

    private void CreateSampleMappingsFile()
    {
        try
        {
            var dir = Path.GetDirectoryName(_adminMappingsPath);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

            var sample = new AdminMappingsFile
            {
                Mappings = new List<AdminMapping>
                {
                    new()
                    {
                        MappingId = Guid.NewGuid().ToString(),
                        ProjectId = Guid.NewGuid().ToString(),
                        ProjectName = "Project Alpha",
                        ModelIdentity = new ModelIdentity
                        {
                            Type = "workshared_central",
                            CentralPath = @"\\SERVER\CENTRAL\PROJECT_A_CENTRAL.RVT",
                            CentralGuid = "11111111-2222-3333-4444-555555555555",
                            DocumentTitle = "Project_A.rvt",
                        },
                        CreatedBy = "admin@company.com",
                        CreatedUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
                        IsActive = true,
                    },
                },
            };

            var json = JsonSerializer.Serialize(sample, new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            });

            File.WriteAllText(_adminMappingsPath, json);
            _logger.LogInformation("Created sample admin mappings at {Path}", _adminMappingsPath);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create sample admin mappings");
        }
    }
}

/// <summary>
/// Represents a resolved model identity.
/// </summary>
public class ModelIdentity
{
    public string Type { get; set; } = ""; // workshared_central, acc_cloud_model, standalone_file, unsaved, unknown
    public string? CentralPath { get; set; }
    public string? CentralGuid { get; set; }
    public string? AccProjectId { get; set; }
    public string? AccModelId { get; set; }
    public string? FilePath { get; set; }
    public string? FileHash { get; set; }
    public long FileSizeBytes { get; set; }
    public string? DocumentTitle { get; set; }
    public string? SessionDocumentId { get; set; }
}

/// <summary>
/// Admin mapping configuration.
/// </summary>
public class AdminMapping
{
    public string MappingId { get; set; } = "";
    public string ProjectId { get; set; } = "";
    public string ProjectName { get; set; } = "";
    public ModelIdentity ModelIdentity { get; set; } = new();
    public string CreatedBy { get; set; } = "";
    public string CreatedUtc { get; set; } = "";
    public bool IsActive { get; set; }
}

public class AdminMappingsFile
{
    public List<AdminMapping> Mappings { get; set; } = new();
}