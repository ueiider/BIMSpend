using System;
using System.Text.Json;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.Extensions.Logging;
using RevitConnector.Identity;
using RevitConnector.Transport;

namespace RevitConnector.Events;

/// <summary>
/// Emits BIMSpend contract events to the transport layer.
/// </summary>
public class EventEmitter
{
    private readonly ITransport _transport;
    private readonly ModelIdentityResolver _identityResolver;
    private readonly ILogger _logger;
    private readonly string _instanceId;
    private readonly int _processId;
    private readonly string _sessionId;

    public EventEmitter(ITransport transport, ModelIdentityResolver identityResolver, ILogger logger)
    {
        _transport = transport;
        _identityResolver = identityResolver;
        _logger = logger;
        _instanceId = Guid.NewGuid().ToString();
        _processId = Environment.ProcessId;
        _sessionId = Guid.NewGuid().ToString(); // Revit session ID
    }

    public void EmitDocumentOpened(Document doc, View activeView)
    {
        var modelIdentity = _identityResolver.Resolve(doc);
        var eventId = Guid.NewGuid().ToString();
        var timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ");

        var evt = new
        {
            event_id = eventId,
            event_type = "revit.document.opened",
            schema_version = "1.0.0",
            timestamp_utc = timestamp,
            source = new
            {
                component = "revit-connector",
                version = GetRevitVersion(),
                instance_id = _instanceId,
                process_id = _processId,
            },
            correlation = new
            {
                session_id = _sessionId,
                run_id = Guid.NewGuid().ToString(),
                external_run_id = GenerateExternalRunId(_instanceId, timestamp),
                external_session_id = GenerateExternalSessionId(_processId, _sessionId),
            },
            payload = new
            {
                document = new
                {
                    document_id = GetDocumentId(doc),
                    title = doc.Title,
                    path = doc.PathName,
                    is_workshared = doc.IsWorkshared,
                    central_path = doc.GetWorksharingCentralModelPath()?.CentralPath ?? "",
                    central_guid = GetCentralGuid(doc),
                    version_number = GetVersionNumber(doc),
                    last_saved_by = GetLastSavedBy(doc),
                    last_saved_utc = GetLastSavedUtc(doc),
                    is_detached = doc.IsDetached,
                    is_new = string.IsNullOrEmpty(doc.PathName),
                },
                view = new
                {
                    view_id = activeView?.Id.IntegerValue ?? 0,
                    view_name = activeView?.Name ?? "",
                    view_type = activeView?.ViewType.ToString() ?? "",
                },
                process = new
                {
                    process_id = _processId,
                    session_id = _sessionId,
                    revit_version = GetRevitVersion(),
                    dotnet_runtime = Environment.Version.ToString(),
                },
            },
        };

        Emit(evt);
    }

    public void EmitDocumentClosed(Document doc, string closeReason)
    {
        var eventId = Guid.NewGuid().ToString();
        var timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ");

        var evt = new
        {
            event_id = eventId,
            event_type = "revit.document.closed",
            schema_version = "1.0.0",
            timestamp_utc = timestamp,
            source = new
            {
                component = "revit-connector",
                version = GetRevitVersion(),
                instance_id = _instanceId,
                process_id = _processId,
            },
            correlation = new
            {
                session_id = _sessionId,
                run_id = Guid.NewGuid().ToString(),
                external_run_id = GenerateExternalRunId(_instanceId, timestamp),
                external_session_id = GenerateExternalSessionId(_processId, _sessionId),
            },
            payload = new
            {
                document_id = GetDocumentId(doc),
                title = doc.Title,
                close_reason = closeReason.ToLowerInvariant().Replace(" ", "_"),
                was_modified = doc.IsModified,
                last_view = new
                {
                    view_id = doc.ActiveView?.Id.IntegerValue ?? 0,
                    view_name = doc.ActiveView?.Name ?? "",
                },
                session_duration_seconds = 0, // Would need session tracking
                process = new
                {
                    process_id = _processId,
                    session_id = _sessionId,
                },
            },
        };

        Emit(evt);
    }

    public void EmitViewActivated(Document doc, View previousView, View currentView)
    {
        var eventId = Guid.NewGuid().ToString();
        var timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ");

        var evt = new
        {
            event_id = eventId,
            event_type = "revit.view.activated",
            schema_version = "1.0.0",
            timestamp_utc = timestamp,
            source = new
            {
                component = "revit-connector",
                version = GetRevitVersion(),
                instance_id = _instanceId,
                process_id = _processId,
            },
            correlation = new
            {
                session_id = _sessionId,
                run_id = Guid.NewGuid().ToString(),
                external_run_id = GenerateExternalRunId(_instanceId, timestamp),
                external_session_id = GenerateExternalSessionId(_processId, _sessionId),
            },
            payload = new
            {
                document_id = GetDocumentId(doc),
                previous_view = new
                {
                    view_id = previousView?.Id.IntegerValue ?? 0,
                    view_name = previousView?.Name ?? "",
                    view_type = previousView?.ViewType.ToString() ?? "",
                },
                current_view = new
                {
                    view_id = currentView.Id.IntegerValue,
                    view_name = currentView.Name,
                    view_type = currentView.ViewType.ToString(),
                },
            },
        };

        Emit(evt);
    }

    public void EmitIdling(Document doc, View activeView, bool isForeground)
    {
        var eventId = Guid.NewGuid().ToString();
        var timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ");

        var evt = new
        {
            event_id = eventId,
            event_type = "revit.application.idling",
            schema_version = "1.0.0",
            timestamp_utc = timestamp,
            source = new
            {
                component = "revit-connector",
                version = GetRevitVersion(),
                instance_id = _instanceId,
                process_id = _processId,
            },
            correlation = new
            {
                session_id = _sessionId,
                run_id = Guid.NewGuid().ToString(),
                external_run_id = GenerateExternalRunId(_instanceId, timestamp),
                external_session_id = GenerateExternalSessionId(_processId, _sessionId),
            },
            payload = new
            {
                document_id = GetDocumentId(doc),
                active_view_id = activeView?.Id.IntegerValue ?? 0,
                is_foreground = isForeground,
                process_id = _processId,
                session_id = _sessionId,
            },
        };

        Emit(evt);
    }

    public void EmitIdentityRemapped(Document doc, string oldPath, string trigger)
    {
        var previousIdentity = _identityResolver.ResolveFromPath(oldPath);
        var newIdentity = _identityResolver.Resolve(doc);

        var eventId = Guid.NewGuid().ToString();
        var timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ");

        var evt = new
        {
            event_id = eventId,
            event_type = "identity.remapped",
            schema_version = "1.0.0",
            timestamp_utc = timestamp,
            source = new
            {
                component = "revit-connector",
                version = GetRevitVersion(),
                instance_id = _instanceId,
                process_id = _processId,
            },
            correlation = new
            {
                session_id = _sessionId,
                run_id = Guid.NewGuid().ToString(),
            },
            payload = new
            {
                previous_identity = previousIdentity,
                new_identity = newIdentity,
                trigger = trigger,
                requires_review = true,
            },
        };

        Emit(evt);
    }

    private void Emit(object evt)
    {
        try
        {
            var json = JsonSerializer.Serialize(evt, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                WriteIndented = false,
            });

            _transport.Send(json);
            _logger.LogDebug("Emitted event: {EventType}", evt.GetType().GetProperty("event_type")?.GetValue(evt));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to emit event");
        }
    }

    private static string GetRevitVersion()
    {
        try
        {
            var assembly = typeof(Document).Assembly;
            var version = assembly.GetName().Version;
            return $"{version?.Major}.{version?.Minor}.{version?.Build}";
        }
        catch
        {
            return "unknown";
        }
    }

    private static string GetDocumentId(Document doc)
    {
        // Use a stable identifier for the document
        // In practice, could use a hash of path + GUID
        var path = doc.PathName;
        var guid = GetCentralGuid(doc);
        var input = $"{path}|{guid}";
        return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(input)))[..32].ToLowerInvariant();
    }

    private static string GetCentralGuid(Document doc)
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

    private static int GetVersionNumber(Document doc)
    {
        try
        {
            var info = BasicFileInfo.Extract(doc.PathName);
            return info.LastSaveVersion;
        }
        catch
        {
            return 0;
        }
    }

    private static string GetLastSavedBy(Document doc)
    {
        try
        {
            var info = BasicFileInfo.Extract(doc.PathName);
            return info.LastSavedBy ?? "";
        }
        catch
        {
            return "";
        }
    }

    private static string GetLastSavedUtc(Document doc)
    {
        try
        {
            var info = BasicFileInfo.Extract(doc.PathName);
            return info.LastSavedTime?.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") ?? "";
        }
        catch
        {
            return "";
        }
    }

    private static string GenerateExternalRunId(string adapterInstanceId, string runStartUtc)
    {
        var input = $"run{adapterInstanceId}{runStartUtc}";
        return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(input)))[..32].ToLowerInvariant();
    }

    private static string GenerateExternalSessionId(int revitProcessId, string revitSessionId)
    {
        var input = $"session{revitProcessId}{revitSessionId}";
        return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(input)))[..32].ToLowerInvariant();
    }
}