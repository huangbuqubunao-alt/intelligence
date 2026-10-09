// One-shot native authorization component; no client arguments, no HTTP server.
#import <AppKit/AppKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#include <stdio.h>

int main(int argc, const char *argv[]) {
    (void)argv;
    if (argc != 1) return 2;
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [app finishLaunching];
        [app activate];
        NSOpenPanel *panel = [NSOpenPanel openPanel];
        panel.title = @"Intelligence — Add local files";
        panel.message = @"Choose files to create independent private snapshots. Originals stay unchanged.";
        panel.canChooseFiles = YES;
        panel.canChooseDirectories = NO;
        panel.resolvesAliases = NO;
        panel.allowsMultipleSelection = YES;
        panel.canDownloadUbiquitousContents = NO;
        NSMutableArray<UTType *> *types = [NSMutableArray array];
        for (NSString *extension in @[@"txt", @"md", @"mp3", @"m4a", @"wav", @"mp4", @"mov", @"m4v"]) {
            UTType *type = [UTType typeWithFilenameExtension:extension];
            if (type) [types addObject:type];
        }
        panel.allowedContentTypes = types;
        NSMutableArray<NSString *> *paths = [NSMutableArray array];
        if ([panel runModal] == NSModalResponseOK) {
            if (panel.URLs.count > 20) return 3;
            for (NSURL *url in panel.URLs) {
                if (!url.isFileURL || url.path.length > 4096) return 4;
                [paths addObject:url.path];
            }
        }
        NSData *output = [NSJSONSerialization dataWithJSONObject:paths options:0 error:NULL];
        if (!output || output.length > 131072) return 5;
        fwrite(output.bytes, 1, output.length, stdout);
        fflush(stdout);
        return 0;
    }
}
