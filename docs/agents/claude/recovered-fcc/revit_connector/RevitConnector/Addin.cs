using System;
using System.IO;
using System.Reflection;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using RevitConnector.Events;
using RevitConnector.Identity;
using RevitConnector.Transport;

namespace RevitConnector;

/// <summary>
/// Main Revit add-in entry point implementing IExternalApplication.
/// </summary>
[Transaction(TransactionMode.Manual)]
[Regeneration(RegenerationOption.Manual)]
public class Addin : IExternalApplication
{
    private static readonly string NamedPipeName = @"\\.\pipe\bimspend_revit_events";
    private static ILogger<Addin> _logger = null!;
    private static EventEmitter _eventEmitter = null!;
    private static ModelIdentityResolver _identityResolver = null!;
    private static NamedPipeTransport _transport = null!;
    private static bool _isShuttingDown = false;

    public Result OnStartup(UIControlledApplication application)
    {
        try
        {
            // Initialize logging
            InitializeLogging();

            _logger.LogInformation("BIMSpend Revit Connector starting up...");

            // Initialize transport (named pipe)
            _transport = new NamedPipeTransport(NamedPipeName);
            _transport.Start();

            // Initialize identity resolver
            var adminMappingsPath = GetAdminMappingsPath();
            _identityResolver = new ModelIdentityResolver(adminMappingsPath, _logger);

            // Initialize event emitter
            _eventEmitter = new EventEmitter(_transport, _identityResolver, _logger);

            // Subscribe to Revit events
            SubscribeToEvents(application);

            _logger.LogInformation("BIMSpend Revit Connector started successfully");
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Failed to start BIMSpend Revit Connector");
            return Result.Failed;
        }
    }

    public Result OnShutdown(UIControlledApplication application)
    {
        try
        {
            _isShuttingDown = true;
            _logger?.LogInformation("BIMSpend Revit Connector shutting down...");

            // Unsubscribe from events
            UnsubscribeFromEvents(application);

            // Flush and close transport
            _transport?.Stop();
            _transport?.Dispose();

            _logger?.LogInformation("BIMSpend Revit Connector stopped");
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Error during shutdown");
            return Result.Failed;
        }
    }

    private void InitializeLogging()
    {
        var logPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "BIMSpend",
            "logs",
            $"revit_connector_{DateTime.UtcNow:yyyyMMdd}.log"
        );

        Directory.CreateDirectory(Path.GetDirectoryName(logPath)!);

        var loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.SetMinimumLevel(LogLevel.Information);
            builder.AddConsole();
            builder.AddFile(logPath);
        });

        _logger = loggerFactory.CreateLogger<Addin>();
    }

    private void SubscribeToEvents(UIControlledApplication application)
    {
        // Application-level document events
        application.Application.DocumentOpened += OnDocumentOpened;
        application.Application.DocumentClosed += OnDocumentClosed;
        application.Application.DocumentSaved += OnDocumentSaved;
        application.Application.DocumentSavedAs += OnDocumentSavedAs;

        // UI application events
        application.ViewActivated += OnViewActivated;

        // Idling event (use sparingly - only for heartbeat)
        application.Idling += OnIdling;

        _logger.LogInformation("Subscribed to Revit events");
    }

    private void UnsubscribeFromEvents(UIControlledApplication application)
    {
        application.Application.DocumentOpened -= OnDocumentOpened;
        application.Application.DocumentClosed -= OnDocumentClosed;
        application.Application.DocumentSaved -= OnDocumentSaved;
        application.Application.DocumentSavedAs -= OnDocumentSavedAs;
        application.ViewActivated -= OnViewActivated;
        application.Idling -= OnIdling;

        _logger.LogInformation("Unsubscribed from Revit events");
    }

    private void OnDocumentOpened(object? sender, DocumentOpenedEventArgs e)
    {
        if (_isShuttingDown) return;

        try
        {
            var doc = e.Document;
            var activeView = doc.ActiveView;

            _logger.LogInformation("Document opened: {Title} ({Path})", doc.Title, doc.PathName);

            _eventEmitter.EmitDocumentOpened(doc, activeView);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling DocumentOpened");
        }
    }

    private void OnDocumentClosed(object? sender, DocumentClosedEventArgs e)
    {
        if (_isShuttingDown) return;

        try
        {
            var doc = e.Document;
            var closeReason = e.GetClosedDocumentReason().ToString();

            _logger.LogInformation("Document closed: {Title} (Reason: {Reason})", doc.Title, closeReason);

            _eventEmitter.EmitDocumentClosed(doc, closeReason);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling DocumentClosed");
        }
    }

    private void OnDocumentSaved(object? sender, DocumentSavedEventArgs e)
    {
        if (_isShuttingDown) return;

        try
        {
            var doc = e.Document;
            _logger.LogInformation("Document saved: {Title}", doc.Title);

            // Check if this was a Save As (new central path)
            // This would trigger an identity remapping event
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling DocumentSaved");
        }
    }

    private void OnDocumentSavedAs(object? sender, DocumentSavedAsEventArgs e)
    {
        if (_isShuttingDown) return;

        try
        {
            var doc = e.Document;
            _logger.LogInformation("Document saved as: {Title} (Old path: {OldPath})", doc.Title, e.OldPathName);

            // Emit identity remapping event
            _eventEmitter.EmitIdentityRemapped(doc, e.OldPathName, "save_as");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling DocumentSavedAs");
        }
    }

    private void OnViewActivated(object? sender, ViewActivatedEventArgs e)
    {
        if (_isShuttingDown) return;

        try
        {
            var doc = e.Document;
            var previousView = e.PreviousActiveView;
            var currentView = e.CurrentActiveView;

            if (previousView != null && currentView != null && previousView.Id != currentView.Id)
            {
                _logger.LogInformation(
                    "View activated: {Prev} -> {Current} in {Doc}",
                    previousView.Name, currentView.Name, doc.Title);

                _eventEmitter.EmitViewActivated(doc, previousView, currentView);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling ViewActivated");
        }
    }

    private void OnIdling(object? sender, IdlingEventArgs e)
    {
        if (_isShuttingDown) return;

        try
        {
            // Only emit idling for foreground document
            var uiApp = sender as UIApplication;
            if (uiApp == null) return;

            var doc = uiApp.ActiveUIDocument?.Document;
            if (doc == null) return;

            // Check if Revit is foreground (simplified - in production use GetForegroundWindow)
            var isForeground = IsRevitForeground();

            var activeView = doc.ActiveView;
            _eventEmitter.EmitIdling(doc, activeView, isForeground);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling Idling");
        }
    }

    private bool IsRevitForeground()
    {
        // In production: use GetForegroundWindow() and compare with Revit process main window
        // For now, return true as placeholder
        return true;
    }

    private string GetAdminMappingsPath()
    {
        var configDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
            "BIMSpend",
            "config"
        );
        return Path.Combine(configDir, "admin_mappings.json");
    }
}

/// <summary>
/// Extension for file logging (simplified - in production use Serilog or similar).
/// </summary>
file static class LoggerFactoryExtensions
{
    public static ILoggingBuilder AddFile(this ILoggingBuilder builder, string path)
    {
        builder.AddProvider(new FileLoggerProvider(path));
        return builder;
    }
}

/// <summary>
/// Simple file logger provider.
/// </summary>
file class FileLoggerProvider : ILoggerProvider
{
    private readonly string _path;
    private readonly object _lock = new();

    public FileLoggerProvider(string path) => _path = path;

    public ILogger CreateLogger(string categoryName) => new FileLogger(_path, _lock);

    public void Dispose() { }
}

file class FileLogger : ILogger
{
    private readonly string _path;
    private readonly object _lock;

    public FileLogger(string path, object lockObj)
    {
        _path = path;
        _lock = lockObj;
    }

    public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
    {
        var message = $"{DateTime.UtcNow:yyyy-MM-ddTHH:mm:ss.fffZ} [{logLevel}] {state}";
        if (exception != null) message += $"\n{exception}";

        lock (_lock)
        {
            File.AppendAllText(_path, message + Environment.NewLine);
        }
    }
}