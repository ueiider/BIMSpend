using System;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using RevitConnector.Transport;

namespace RevitConnector.Transport;

/// <summary>
/// Named pipe transport for communication between Revit Connector and Windows Adapter.
/// </summary>
public class NamedPipeTransport : ITransport
{
    private readonly string _pipeName;
    private readonly ILogger _logger;
    private NamedPipeServerStream? _pipeServer;
    private CancellationTokenSource? _cancellationToken;
    private Task? _listenTask;

    public event Action<string>? MessageReceived;

    public NamedPipeTransport(string pipeName, ILogger? logger = null)
    {
        _pipeName = pipeName;
        _logger = logger ?? Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance;
    }

    public void Start()
    {
        _cancellationToken = new CancellationTokenSource();
        _listenTask = Task.Run(ListenAsync, _cancellationToken.Token);
        _logger.LogInformation("Named pipe transport started: {PipeName}", _pipeName);
    }

    public void Stop()
    {
        _cancellationToken?.Cancel();
        _pipeServer?.Close();
        _listenTask?.Wait(TimeSpan.FromSeconds(5));
        _logger.LogInformation("Named pipe transport stopped");
    }

    public void Send(string jsonMessage)
    {
        // In this implementation, Revit Connector is the server
        // Windows Adapter connects as client and reads messages
        // For bidirectional, we'd need a different approach
        // For now, we write to a file drop zone as fallback
        WriteToDropZone(jsonMessage);
    }

    public void Dispose()
    {
        Stop();
        _pipeServer?.Dispose();
        _cancellationToken?.Dispose();
    }

    private async Task ListenAsync()
    {
        while (!_cancellationToken.IsCancellationRequested)
        {
            try
            {
                _pipeServer = new NamedPipeServerStream(
                    Path.GetFileName(_pipeName),
                    PipeDirection.InOut,
                    1, // max instances
                    PipeTransmissionMode.Message,
                    PipeOptions.Asynchronous);

                _logger.LogDebug("Waiting for client connection...");
                await _pipeServer.WaitForConnectionAsync(_cancellationToken.Token);

                _logger.LogInformation("Client connected to named pipe");

                // Read messages from client (Windows Adapter)
                using var reader = new StreamReader(_pipeServer, Encoding.UTF8, detectEncodingFromByteOrderMarks: true, bufferSize: 4096, leaveOpen: true);

                while (_pipeServer.IsConnected && !_cancellationToken.IsCancellationRequested)
                {
                    var line = await reader.ReadLineAsync();
                    if (line == null) break; // Client disconnected

                    MessageReceived?.Invoke(line);
                }
            }
            catch (OperationCanceledException)
            {
                break; // Expected on shutdown
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Named pipe error");
                await Task.Delay(1000, _cancellationToken.Token); // Backoff before retry
            }
            finally
            {
                _pipeServer?.Close();
                _pipeServer?.Dispose();
                _pipeServer = null;
            }
        }
    }

    private void WriteToDropZone(string jsonMessage)
    {
        try
        {
            var dropZone = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "BIMSpend",
                "dropzone"
            );

            Directory.CreateDirectory(dropZone);

            var fileName = $"revit_event_{DateTime.UtcNow:yyyyMMdd_HHmmss_fff}_{Guid.NewGuid():N}.json";
            var filePath = Path.Combine(dropZone, fileName);

            File.WriteAllText(filePath, jsonMessage);
            _logger.LogDebug("Wrote event to drop zone: {File}", fileName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to write to drop zone");
        }
    }
}