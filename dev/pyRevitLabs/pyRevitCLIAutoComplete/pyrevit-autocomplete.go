package main

import (
	"github.com/posener/complete"
)

func main() {
	pyrevit := complete.Command{
		Sub: complete.Commands{
			"wiki": complete.Command{
				Sub:   complete.Commands{},
				Flags: complete.Flags{},
			},
			"blog": complete.Command{
				Sub:   complete.Commands{},
				Flags: complete.Flags{},
			},
			"docs": complete.Command{
				Sub:   complete.Commands{},
				Flags: complete.Flags{},
			},
			"source": complete.Command{
				Sub:   complete.Commands{},
				Flags: complete.Flags{},
			},
			"youtube": complete.Command{
				Sub:   complete.Commands{},
				Flags: complete.Flags{},
			},
			"support": complete.Command{
				Sub:   complete.Commands{},
				Flags: complete.Flags{},
			},
			"env": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
<<<<<<< HEAD
					"--log":  complete.PredictNothing,
					"--json": complete.PredictNothing,
					"--help": complete.PredictNothing,
=======
<<<<<<< HEAD
=======
					"--json": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
					"--help": complete.PredictNothing,
					"--log":  complete.PredictNothing,
					"--json": complete.PredictNothing,
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
				},
			},
			"update": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
					"--help": complete.PredictNothing,
				},
			},
			"clone": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
<<<<<<< HEAD
					"--log":      complete.PredictNothing,
					"--help":     complete.PredictNothing,
					"--token":    complete.PredictNothing,
					"--dest":     complete.PredictNothing,
					"--branch":   complete.PredictNothing,
					"--password": complete.PredictNothing,
=======
<<<<<<< HEAD
					"--password": complete.PredictNothing,
					"--dest":     complete.PredictNothing,
					"--token":    complete.PredictNothing,
					"--help":     complete.PredictNothing,
=======
					"--token":    complete.PredictNothing,
					"--dest":     complete.PredictNothing,
					"--help":     complete.PredictNothing,
					"--log":      complete.PredictNothing,
					"--password": complete.PredictNothing,
					"--image":    complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
					"--branch":   complete.PredictNothing,
					"--log":      complete.PredictNothing,
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
					"--image":    complete.PredictNothing,
				},
			},
			"clones": complete.Command{
				Sub: complete.Commands{
					"info": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"open": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"add": complete.Command{
						Sub: complete.Commands{
							"this": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--force": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--force": complete.PredictNothing,
						},
					},
					"forget": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"rename": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"delete": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--clearconfigs": complete.PredictNothing,
						},
					},
					"branch": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"version": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"commit": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"origin": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log":   complete.PredictNothing,
							"--reset": complete.PredictNothing,
						},
					},
					"update": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
<<<<<<< HEAD
							"--log":      complete.PredictNothing,
=======
<<<<<<< HEAD
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
							"--password": complete.PredictNothing,
							"--log":      complete.PredictNothing,
							"--token":    complete.PredictNothing,
=======
							"--token":    complete.PredictNothing,
<<<<<<< HEAD
=======
							"--log":      complete.PredictNothing,
							"--password": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
						},
					},
					"deployments": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"engines": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
				},
				Flags: complete.Flags{
					"--help": complete.PredictNothing,
				},
			},
			"attach": complete.Command{
				Sub: complete.Commands{
					"default": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
<<<<<<< HEAD
							"--allusers":  complete.PredictNothing,
							"--attached":  complete.PredictNothing,
							"--installed": complete.PredictNothing,
=======
<<<<<<< HEAD
							"--allusers":  complete.PredictNothing,
							"--attached":  complete.PredictNothing,
							"--installed": complete.PredictNothing,
=======
							"--installed": complete.PredictNothing,
							"--attached":  complete.PredictNothing,
							"--allusers":  complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
						},
					},
				},
				Flags: complete.Flags{
<<<<<<< HEAD
					"--allusers":  complete.PredictNothing,
					"--attached":  complete.PredictNothing,
					"--installed": complete.PredictNothing,
					"--help":      complete.PredictNothing,
=======
<<<<<<< HEAD
					"--allusers":  complete.PredictNothing,
					"--attached":  complete.PredictNothing,
					"--help":      complete.PredictNothing,
=======
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
					"--installed": complete.PredictNothing,
					"--attached":  complete.PredictNothing,
					"--help":      complete.PredictNothing,
					"--allusers":  complete.PredictNothing,
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
				},
			},
			"attached": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
					"--help": complete.PredictNothing,
				},
			},
			"switch": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
					"--help": complete.PredictNothing,
				},
			},
			"detach": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
					"--log":  complete.PredictNothing,
					"--help": complete.PredictNothing,
				},
			},
			"extend": complete.Command{
				Sub: complete.Commands{
					"ui": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
<<<<<<< HEAD
							"--log":      complete.PredictNothing,
							"--password": complete.PredictNothing,
							"--token":    complete.PredictNothing,
							"--dest":     complete.PredictNothing,
=======
<<<<<<< HEAD
							"--password": complete.PredictNothing,
							"--log":      complete.PredictNothing,
							"--dest":     complete.PredictNothing,
							"--token":    complete.PredictNothing,
=======
							"--token":    complete.PredictNothing,
							"--password": complete.PredictNothing,
							"--log":      complete.PredictNothing,
							"--dest":     complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
						},
					},
					"lib": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
<<<<<<< HEAD
							"--log":      complete.PredictNothing,
							"--password": complete.PredictNothing,
							"--token":    complete.PredictNothing,
							"--dest":     complete.PredictNothing,
=======
<<<<<<< HEAD
							"--password": complete.PredictNothing,
							"--log":      complete.PredictNothing,
							"--dest":     complete.PredictNothing,
							"--token":    complete.PredictNothing,
=======
							"--token":    complete.PredictNothing,
							"--password": complete.PredictNothing,
							"--log":      complete.PredictNothing,
							"--dest":     complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
						},
					},
				},
				Flags: complete.Flags{
<<<<<<< HEAD
					"--log":      complete.PredictNothing,
					"--token":    complete.PredictNothing,
					"--help":     complete.PredictNothing,
					"--dest":     complete.PredictNothing,
					"--password": complete.PredictNothing,
=======
<<<<<<< HEAD
					"--password": complete.PredictNothing,
					"--dest":     complete.PredictNothing,
					"--token":    complete.PredictNothing,
					"--help":     complete.PredictNothing,
					"--log":      complete.PredictNothing,
=======
					"--token":    complete.PredictNothing,
					"--dest":     complete.PredictNothing,
					"--help":     complete.PredictNothing,
					"--log":      complete.PredictNothing,
					"--password": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
				},
			},
			"extensions": complete.Command{
				Sub: complete.Commands{
					"search": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"info": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"help": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"open": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
					"delete": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"origin": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log":   complete.PredictNothing,
							"--reset": complete.PredictNothing,
						},
					},
					"paths": complete.Command{
						Sub: complete.Commands{
							"forget": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
									"--all": complete.PredictNothing,
								},
							},
							"add": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log":  complete.PredictNothing,
							"--help": complete.PredictNothing,
						},
					},
					"enable": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"disable": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"sources": complete.Command{
						Sub: complete.Commands{
							"forget": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
									"--all": complete.PredictNothing,
								},
							},
							"add": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log":  complete.PredictNothing,
							"--help": complete.PredictNothing,
						},
					},
					"update": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
<<<<<<< HEAD
							"--log":      complete.PredictNothing,
=======
<<<<<<< HEAD
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
							"--password": complete.PredictNothing,
							"--log":      complete.PredictNothing,
							"--token":    complete.PredictNothing,
=======
							"--token":    complete.PredictNothing,
<<<<<<< HEAD
=======
							"--log":      complete.PredictNothing,
							"--password": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
						},
					},
				},
				Flags: complete.Flags{
					"--log":  complete.PredictNothing,
					"--help": complete.PredictNothing,
				},
			},
			"releases": complete.Command{
				Sub: complete.Commands{
					"latest": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--pre": complete.PredictNothing,
						},
					},
					"open": complete.Command{
						Sub: complete.Commands{
							"latest": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--pre": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--pre": complete.PredictNothing,
						},
					},
					"download": complete.Command{
						Sub: complete.Commands{
							"installer": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--dest": complete.PredictNothing,
								},
							},
							"archive": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--dest": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--dest": complete.PredictNothing,
						},
					},
				},
				Flags: complete.Flags{
					"--pre":  complete.PredictNothing,
					"--help": complete.PredictNothing,
				},
			},
			"revits": complete.Command{
				Sub: complete.Commands{
					"killall": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"fileinfo": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--rft": complete.PredictNothing,
							"--rte": complete.PredictNothing,
							"--csv": complete.PredictNothing,
						},
					},
				},
				Flags: complete.Flags{
<<<<<<< HEAD
					"--supported": complete.PredictNothing,
					"--installed": complete.PredictNothing,
					"--help":      complete.PredictNothing,
=======
<<<<<<< HEAD
					"--supported": complete.PredictNothing,
					"--help":      complete.PredictNothing,
					"--installed": complete.PredictNothing,
=======
					"--installed": complete.PredictNothing,
					"--help":      complete.PredictNothing,
					"--supported": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
				},
			},
			"run": complete.Command{
				Sub: complete.Commands{
					"commands": complete.Command{
						Sub:   complete.Commands{},
						Flags: complete.Flags{},
					},
				},
				Flags: complete.Flags{
<<<<<<< HEAD
					"--import":       complete.PredictNothing,
					"--help":         complete.PredictNothing,
					"--allowdialogs": complete.PredictNothing,
					"--purge":        complete.PredictNothing,
=======
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
					"--models":       complete.PredictNothing,
					"--help":         complete.PredictNothing,
					"--revit":        complete.PredictNothing,
<<<<<<< HEAD
					"--allowdialogs": complete.PredictNothing,
					"--purge":        complete.PredictNothing,
					"--import":       complete.PredictNothing,
=======
					"--import":       complete.PredictNothing,
					"--help":         complete.PredictNothing,
					"--purge":        complete.PredictNothing,
					"--allowdialogs": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
				},
			},
			"caches": complete.Command{
				Sub: complete.Commands{
					"bim360": complete.Command{
						Sub: complete.Commands{
							"clear": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{},
					},
				},
				Flags: complete.Flags{
					"--help": complete.PredictNothing,
				},
			},
			"config": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
					"--from": complete.PredictNothing,
					"--help": complete.PredictNothing,
				},
			},
			"configs": complete.Command{
				Sub: complete.Commands{
					"bincache": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"checkupdates": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"autoupdate": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"rocketmode": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"logs": complete.Command{
						Sub: complete.Commands{
							"none": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"verbose": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"debug": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"filelogging": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"startuptimeout": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"loadbeta": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"cpyversion": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"usercanupdate": complete.Command{
						Sub: complete.Commands{
							"yes": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"no": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"usercanextend": complete.Command{
						Sub: complete.Commands{
							"yes": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"no": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"usercanconfig": complete.Command{
						Sub: complete.Commands{
							"yes": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"no": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"colordocs": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"tooltipdebuginfo": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"routes": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"port": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"coreapi": complete.Command{
								Sub: complete.Commands{
									"enable": complete.Command{
										Sub: complete.Commands{},
										Flags: complete.Flags{
											"--log": complete.PredictNothing,
										},
									},
									"disable": complete.Command{
										Sub: complete.Commands{},
										Flags: complete.Flags{
											"--log": complete.PredictNothing,
										},
									},
								},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log":  complete.PredictNothing,
							"--help": complete.PredictNothing,
						},
					},
					"telemetry": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"utc": complete.Command{
								Sub: complete.Commands{
									"yes": complete.Command{
										Sub: complete.Commands{},
										Flags: complete.Flags{
											"--log": complete.PredictNothing,
										},
									},
									"no": complete.Command{
										Sub: complete.Commands{},
										Flags: complete.Flags{
											"--log": complete.PredictNothing,
										},
									},
								},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"file": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"server": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"hooks": complete.Command{
								Sub: complete.Commands{
									"yes": complete.Command{
										Sub: complete.Commands{},
										Flags: complete.Flags{
											"--log": complete.PredictNothing,
										},
									},
									"no": complete.Command{
										Sub: complete.Commands{},
										Flags: complete.Flags{
											"--log": complete.PredictNothing,
										},
									},
								},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log":  complete.PredictNothing,
							"--help": complete.PredictNothing,
						},
					},
					"apptelemetry": complete.Command{
						Sub: complete.Commands{
							"enable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"disable": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"flags": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
							"server": complete.Command{
								Sub: complete.Commands{},
								Flags: complete.Flags{
									"--log": complete.PredictNothing,
								},
							},
						},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"outputcss": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"seed": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--lock": complete.PredictNothing,
						},
					},
					"enable": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
					"disable": complete.Command{
						Sub: complete.Commands{},
						Flags: complete.Flags{
							"--log": complete.PredictNothing,
						},
					},
				},
				Flags: complete.Flags{
					"--log":  complete.PredictNothing,
					"--help": complete.PredictNothing,
				},
			},
			"doctor": complete.Command{
				Sub: complete.Commands{},
				Flags: complete.Flags{
					"--list":   complete.PredictNothing,
					"--help":   complete.PredictNothing,
					"--dryrun": complete.PredictNothing,
				},
			},
		},
		Flags: complete.Flags{
<<<<<<< HEAD
			"--verbose": complete.PredictNothing,
			"--usage":   complete.PredictNothing,
			"--help":    complete.PredictNothing,
			"--version": complete.PredictNothing,
			"--debug":   complete.PredictNothing,
=======
<<<<<<< HEAD
			"--version": complete.PredictNothing,
			"--verbose": complete.PredictNothing,
			"--help":    complete.PredictNothing,
			"--usage":   complete.PredictNothing,
			"--debug":   complete.PredictNothing,
=======
			"--debug":   complete.PredictNothing,
			"--help":    complete.PredictNothing,
			"--usage":   complete.PredictNothing,
			"--version": complete.PredictNothing,
			"--verbose": complete.PredictNothing,
>>>>>>> e16430e8aeb8682d32a482634cd7a30273655e28
>>>>>>> 31ab6878c4dc2f642a734320882ea92867626f4f
		},
	}
	complete.New("pyrevit", pyrevit).Run()
}
