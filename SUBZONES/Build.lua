-- tools/install_beta.cmd overwrites this in the installed copy with the git commit,
-- so /subzones debug shows which build is running. Release zips keep nil.
local _, ns = ...
ns.Build = nil
