package main

import "github.com/posener/complete"

func main() {

	pyrevit := complete.Command{
		Sub: complete.Commands{
			"help":    complete.Command{},
			"blog":    complete.Command{},
			"docs":    complete.Command{},
			"source":  complete.Command{},
			"youtube": complete.Command{},
			"support": complete.Command{},
			"env": complete.Command{
				Flags: complete.Flags{
					"--json": complete.PredictAnything,
				},
			},
			"clone": complete.Command{
				Flags: complete.Flags{
					"--dest=":   complete.PredictAnything,
					"--source=": complete.PredictAnything,
					"--branch=": complete.PredictAnything,
					"--image=":  complete.PredictAnything,
				},
			},
			"clones": complete.Command{
				Sub: complete.Commands{
					"info": complete.Command{},
					"open": complete.Command{},
					"add":  complete.Command{},
					"forget": complete.Command{
						Flags: complete.Flags{
							"--all": complete.PredictAnything,
						},
					},
					"rename": complete.Command{},
					"delete": complete.Command{
						Flags: complete.Flags{
							"--all": complete.PredictAnything,
						},
					},
					"branch":  complete.Command{},
					"version": complete.Command{},
					"commit":  complete.Command{},
					"origin": complete.Command{
						Flags: complete.Flags{
							"--reset": complete.PredictAnything,
						},
					},
					"update": complete.Command{
						Flags: complete.Flags{
							"--all": complete.PredictAnything,
						},
					},
					"deployments": complete.Command{},
					"engines":     complete.Command{},
				},
			},
			"attach": complete.Command{
				Sub: complete.Commands{
					"latest":     complete.Command{},
					"dynamosafe": complete.Command{},
				},
				Flags: complete.Flags{
					"--installed": complete.PredictAnything,
					"--attached":  complete.PredictAnything,
					"--allusers":  complete.PredictAnything,
				},
			},
			"switch": complete.Command{},
			"detach": complete.Command{
				Flags: complete.Flags{
					"--all": complete.PredictAnything,
				},
			},
			"attached": complete.Command{},
			"extend": complete.Command{
				Sub: complete.Commands{
					"ui":  complete.Command{},
					"lib": complete.Command{},
					"run": complete.Command{},
				},
				Flags: complete.Flags{
					"--dest=":   complete.PredictAnything,
					"--branch=": complete.PredictAnything,
				},
			},
			"extension": complete.Command{
				Sub: complete.Commands{
					"search": complete.Command{},
					"info":   complete.Command{},
					"help":   complete.Command{},
					"open":   complete.Command{},
					"delete": complete.Command{},
					"origin": complete.Command{
						Flags: complete.Flags{
							"--reset": complete.PredictAnything,
						},
					},
					"paths": complete.Command{
						Sub: complete.Commands{
							"add": complete.Command{},
							"forget": complete.Command{
								Flags: complete.Flags{
									"--all": complete.PredictAnything,
								},
							},
						},
					},
					"enable":  complete.Command{},
					"disable": complete.Command{},
					"sources": complete.Command{
						Sub: complete.Commands{
							"add": complete.Command{},
							"forget": complete.Command{
								Flags: complete.Flags{
									"--all": complete.PredictAnything,
								},
							},
						},
					},
					"update": complete.Command{
						Flags: complete.Flags{
							"--all": complete.PredictAnything,
						},
					},
				},
			},
			"releases": complete.Command{
				Sub: complete.Commands{
					"latest": complete.Command{
						Flags: complete.Flags{
							"--pre": complete.PredictAnything,
						},
					},
					"open": complete.Command{
						Flags: complete.Flags{
							"latest": complete.PredictAnything,
							"--pre":  complete.PredictAnything,
						},
					},
					"download": complete.Command{
						Sub: complete.Commands{
							"installer": complete.Command{
								Flags: complete.Flags{
									"--dest=": complete.PredictAnything,
									"--pre":   complete.PredictAnything,
								},
							},
							"archive": complete.Command{
								Flags: complete.Flags{
									"--dest=": complete.PredictAnything,
									"--pre":   complete.PredictAnything,
								},
							},
						},
					},
				},
				Flags: complete.Flags{
					"latest":  complete.PredictAnything,
					"--pre":   complete.PredictAnything,
					"--notes": complete.PredictAnything,
				},
			},
			"image": complete.Command{
				Flags: complete.Flags{
					"--config=": complete.PredictAnything,
					"--dest=":   complete.PredictAnything,
				},
			},
			"revits": complete.Command{
				Sub: complete.Commands{
					"killall": complete.Command{},
					"fileinfo": complete.Command{
						Flags: complete.Flags{
							"--csv=": complete.PredictAnything,
						},
					},
					"addons": complete.Command{
						Sub: complete.Commands{
							"prepare": complete.Command{
								Flags: complete.Flags{
									"--allusers": complete.PredictAnything,
								},
							},
							"install": complete.Command{
								Flags: complete.Flags{
									"--allusers": complete.PredictAnything,
									"--dest=":    complete.PredictAnything,
								},
							},
							"uninstall": complete.Command{},
						},
					},
				},
				Flags: complete.Flags{
					"--installed": complete.PredictAnything,
				},
			},
			"run": complete.Command{
				Flags: complete.Flags{
					"--revit=": complete.PredictAnything,
					"--purge":  complete.PredictAnything,
					"--import": complete.PredictAnything,
				},
			},
			"init": complete.Command{
				Sub: complete.Commands{
					"ui":        complete.Command{},
					"lib":       complete.Command{},
					"run":       complete.Command{},
					"tab":       complete.Command{},
					"panel":     complete.Command{},
					"panelopt":  complete.Command{},
					"pull":      complete.Command{},
					"split":     complete.Command{},
					"splitpush": complete.Command{},
					"push":      complete.Command{},
					"smart":     complete.Command{},
					"command":   complete.Command{},
				},
				Flags: complete.Flags{
					"--usetemplate": complete.PredictAnything,
					"--templates=":  complete.PredictAnything,
				},
			},
			"caches": complete.Command{
				Sub: complete.Commands{
					"clear": complete.Command{},
				},
				Flags: complete.Flags{
					"--all": complete.PredictAnything,
				},
			},
			"config": complete.Command{},
			"configs": complete.Command{
				Sub: complete.Commands{
					"logs": complete.Command{
						Sub: complete.Commands{
							"none":    complete.Command{},
							"verbose": complete.Command{},
							"debug":   complete.Command{},
						},
					},
					"allowremotedll": complete.Command{
						Sub: complete.Commands{
							"enable":  complete.Command{},
							"disable": complete.Command{},
						},
					},
					"checkupdates": complete.Command{
						Sub: complete.Commands{
							"enable":  complete.Command{},
							"disable": complete.Command{},
						},
					},
					"autoupdate": complete.Command{
						Sub: complete.Commands{
							"enable":  complete.Command{},
							"disable": complete.Command{},
						},
					},
					"rocketmode": complete.Command{
						Sub: complete.Commands{
							"enable":  complete.Command{},
							"disable": complete.Command{},
						},
					},
					"filelogging": complete.Command{
						Sub: complete.Commands{
							"enable":  complete.Command{},
							"disable": complete.Command{},
						},
					},
					"loadbeta": complete.Command{
						Sub: complete.Commands{
							"enable":  complete.Command{},
							"disable": complete.Command{},
						},
					},
					"usercanupdate": complete.Command{
						Sub: complete.Commands{
							"Yes": complete.Command{},
							"No":  complete.Command{},
						},
					},
					"usercanextend": complete.Command{
						Sub: complete.Commands{
							"Yes": complete.Command{},
							"No":  complete.Command{},
						},
					},
					"usercanconfig": complete.Command{
						Sub: complete.Commands{
							"Yes": complete.Command{},
							"No":  complete.Command{},
						},
					},
					"usagelogging": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{
									"file":   complete.Command{},
									"server": complete.Command{},
								},
							},
							"disable": complete.Command{},
						},
					},
					"outputcss": complete.Command{},
					"seed": complete.Command{
						Flags: complete.Flags{
							"--lock": complete.PredictAnything,
						},
					},
				},
				Flags: complete.Flags{
					"--all": complete.PredictAnything,
				},
			},
			"cli": complete.Command{
				Sub: complete.Commands{
					"addshortcut": complete.Command{
						Flags: complete.Flags{
							"--desc=":    complete.PredictAnything,
							"--allusers": complete.PredictAnything,
						},
					},
					"installautocomplete": complete.Command{},
				},
			},
		},

		Flags: complete.Flags{
			"-V":        complete.PredictNothing,
			"--version": complete.PredictNothing,
			"--usage":   complete.PredictNothing,
		},

		GlobalFlags: complete.Flags{
			"-h":        complete.PredictNothing,
			"--help":    complete.PredictNothing,
			"--verbose": complete.PredictNothing,
			"--debug":   complete.PredictNothing,
			"--log=":    complete.PredictNothing,
		},
	}

	complete.New("pyrevit", pyrevit).Run()
}
