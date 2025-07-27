---
title: Golang's native tracing and profiling tools
date: 2025-03-07
tags: tech
---
# Golang's native tracing and profiling tools
## Instrumentation Code

### Put this at the start before your primary program code
```go
// Set up CPU profiling
cpuFile, err := os.Create("cpu.prof")
if err != nil {
    panic(err)
}
defer cpuFile.Close()
if err := pprof.StartCPUProfile(cpuFile); err != nil {
    panic(err)
}
defer pprof.StopCPUProfile()

// Set up trace file
traceFile, err := os.Create("trace.out")
if err != nil {
    panic(err)
}
defer traceFile.Close()

err = trace.Start(traceFile)
if err != nil {
    panic(err)
}
defer trace.Stop()

// ... Program code here ...

```

### Put this at the end
```
// Create memory profile
memFile, err := os.Create("mem.prof")
if err != nil {
    panic(err)
}
defer memFile.Close()
if err := pprof.WriteHeapProfile(memFile); err != nil {
    panic(err)
}
```
