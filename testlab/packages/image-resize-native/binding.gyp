{
  "comment": "BAWABU TEST FIXTURE — harmless. A binding.gyp makes npm run node-gyp to compile native code on install, exactly like sharp or bcrypt. This is a LEGITIMATE pattern that must not be flagged.",
  "targets": [
    {
      "target_name": "resize",
      "sources": ["src/resize.cc"]
    }
  ]
}
