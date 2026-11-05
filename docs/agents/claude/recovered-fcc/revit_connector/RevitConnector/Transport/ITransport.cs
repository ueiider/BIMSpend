using System;

namespace RevitConnector.Transport;

/// <summary>
/// Transport interface for sending events from Revit Connector to Windows Adapter.
/// </summary>
public interface ITransport : IDisposable
{
    void Start();
    void Stop();
    void Send(string jsonMessage);
    event Action<string>? MessageReceived;
}