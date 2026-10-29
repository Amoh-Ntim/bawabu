// BAWABU TEST FIXTURE — harmless. A minimal native addon so node-gyp has something to build.
#include <node.h>

namespace {
void Resize(const v8::FunctionCallbackInfo<v8::Value>& args) {
  args.GetReturnValue().Set(v8::Boolean::New(args.GetIsolate(), true));
}

void Init(v8::Local<v8::Object> exports) {
  NODE_SET_METHOD(exports, "resize", Resize);
}

NODE_MODULE(NODE_GYP_MODULE_NAME, Init)
}  // namespace
