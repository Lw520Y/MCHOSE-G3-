$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class G3Probe {
    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_SetOutputReport(IntPtr h, byte[] buf, int len);
    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_GetInputReport(IntPtr h, byte[] buf, int len);
    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_SetFeature(IntPtr h, byte[] buf, int len);
    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_GetFeature(IntPtr h, byte[] buf, int len);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr CreateFile(string path, uint access, uint share, IntPtr sa, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr h);
    [DllImport("kernel32.dll")]
    public static extern void Sleep(uint ms);

    const uint GENERIC_READ = 0x80000000;
    const uint GENERIC_WRITE = 0x40000000;
    const uint FILE_SHARE_READ = 1;
    const uint FILE_SHARE_WRITE = 2;
    const uint OPEN_EXISTING = 3;

    public static string Run(string path) {
        var sb = new StringBuilder();
        IntPtr h = CreateFile(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, 0, IntPtr.Zero);
        if (h.ToInt64() == -1) return "OPEN FAIL err=" + Marshal.GetLastWin32Error();
        try {
            byte[] req = new byte[65];
            req[0] = 0;
            req[1] = 0x55; req[2] = 0x30; req[3] = 0xA5; req[4] = 0x0B; req[5] = 0x2E;
            req[6] = 1; req[7] = 1; req[8] = 1;

            bool ok = HidD_SetOutputReport(h, req, req.Length);
            sb.AppendLine("SetOutputReport ok=" + ok + " err=" + Marshal.GetLastWin32Error());
            if (!ok) {
                bool ok2 = HidD_SetFeature(h, req, req.Length);
                sb.AppendLine("SetFeature ok=" + ok2 + " err=" + Marshal.GetLastWin32Error());
            }
            Sleep(150);

            for (int i = 0; i < 12; i++) {
                byte[] inbuf = new byte[65];
                inbuf[0] = 0;
                bool r = HidD_GetInputReport(h, inbuf, inbuf.Length);
                int err = Marshal.GetLastWin32Error();
                sb.AppendLine("GetInputReport #" + i + " ok=" + r + " err=" + err + " data=" + BitConverter.ToString(inbuf));
                int at = (inbuf[0] == 0xAA && inbuf[1] == 0x30) ? 0 : ((inbuf[1] == 0xAA && inbuf[2] == 0x30) ? 1 : -1);
                if (at >= 0) {
                    sb.AppendLine("FOUND level=" + inbuf[at + 8] + " charge=" + inbuf[at + 9]);
                    break;
                }
                Sleep(100);
            }
        }
        finally {
            CloseHandle(h);
        }
        return sb.ToString();
    }
}
"@

$ff01 = '\\?\HID#VID_258A&PID_0138&MI_01&Col06#7&1cd81421&0&0005#{4d1e55b2-f16f-11cf-88cb-001111000030}'
$ff02 = '\\?\HID#VID_258A&PID_0138&MI_01&Col07#7&1cd81421&0&0006#{4d1e55b2-f16f-11cf-88cb-001111000030}'
Write-Output '=== FF01 ==='
Write-Output ([G3Probe]::Run($ff01))
Write-Output '=== FF02 ==='
Write-Output ([G3Probe]::Run($ff02))

